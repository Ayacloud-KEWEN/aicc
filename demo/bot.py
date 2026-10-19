"""Voice ordering bot: one Pipecat pipeline per browser call (WebRTC).

Pipeline: browser mic -> STT -> context -> LLM (with tools) -> TTS -> browser speaker.
The LLM never edits orders itself: every cart change, order and reservation goes
through a tool, and every change is pushed to the web page over the data channel.
"""

import re
import time
from difflib import SequenceMatcher

import numpy as np
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    FunctionCallsStartedFrame,
    InputAudioRawFrame,
    InterimTranscriptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesAppendFrame,
    LLMTextFrame,
    OutputTransportMessageUrgentFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.turns.user_start.min_words_user_turn_start_strategy import MinWordsUserTurnStartStrategy
from pipecat.turns.types import ProcessFrameResult
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

import payments
import providers
from restaurant import (
    MAX_COVERS_PER_SLOT,
    MENU_BY_ID,
    RESTAURANT,
    Cart,
    menu_for_prompt,
    nearby_free_slots,
    now_paris,
    parse_slot,
    store,
)

LANG_NAMES = {"fr": "French", "en": "English", "zh": "Simplified Chinese (Mandarin)"}

# How to write prices so the TTS voice reads them the way a native speaker says them.
PRICE_RULES = {
    "fr": 'Write prices in words the French way: 11.5 -> "onze euros cinquante", 29 -> "vingt-neuf euros", 7.25 -> "sept euros vingt-cinq".',
    "en": 'Write prices in words: 11.5 -> "eleven euros fifty", 29 -> "twenty-nine euros", 7.25 -> "seven euros twenty-five".',
    "zh": '价格用中文数字、按中文习惯写成“X点Y欧元”：11.5 写“十一点五欧元”，29 写“二十九欧元”，7.25 写“七点二五欧元”，21.5 写“二十一点五欧元”。'
          '绝对不要写成“十一欧元五十”这类法语语序，也不要写阿拉伯数字。',
}

# What to say once the pay button is on screen (the model adapts it; it never asks for card numbers).
PAY_NOW_PHRASES = {
    "fr": "Le bouton « Payer » vient d'apparaître sur votre écran : vous saisissez votre carte sur la page sécurisée de Stripe, je ne vous demanderai jamais votre numéro de carte.",
    "en": "A Pay button has just appeared on your screen: you enter your card on Stripe's secure page, and I will never ask for your card number.",
    "zh": "屏幕上已经出现了“支付”按钮，请在 Stripe 的安全页面上输入银行卡信息，我不会在电话里询问您的卡号。",
}


def payment_rules(lang: str) -> str:
    if not payments.enabled():
        return "- Payment is made at pickup (cash or card at the counter). Call place_order with payment=pay_at_pickup."
    return f"""- Before calling place_order, ask how the customer wants to pay: now online (card, Apple Pay or Google Pay on a secure page shown on their screen) or at pickup. Pass payment=pay_now or payment=pay_at_pickup.
- NEVER ask for, repeat or write down card numbers, expiry dates or security codes. If the customer starts reading card details aloud, stop them politely and point to the pay button.
- After place_order with pay_now, give the order number and the total, then say something like: "{PAY_NOW_PHRASES[lang]}" Then wait: you will receive a system message when the payment arrives; thank the customer then.
- If place_order returns payment_fallback, tell the customer online payment is unavailable right now and they can pay at pickup."""


GREETINGS = {
    "fr": "Bonjour et degemer mat au Restaurant Quimper ! Ici l'assistant virtuel. Je peux prendre votre commande à emporter ou réserver une table. Que puis-je faire pour vous ?",
    "en": "Hello, welcome to Restaurant Quimper! This is the virtual assistant. I can take a takeaway order or book a table for you. How can I help?",
    "zh": "您好，欢迎致电坎佩尔布列塔尼餐厅，我是AI语音助手，可以帮您点外带餐或预订座位，请问有什么可以帮您？",
}


def system_prompt(lang: str) -> str:
    today = now_paris()
    return f"""You are the phone assistant of the restaurant "{RESTAURANT['name']}" ({RESTAURANT['address']}), a Breton crêperie and restaurant in Paris (Montparnasse) named after the town of Quimper in Brittany.
You are talking to a customer by voice. Speak {LANG_NAMES[lang]} only, unless the customer clearly switches language.
You are an AI assistant and you say so if asked.

Today is {today.strftime('%A %Y-%m-%d')}, current time {today.strftime('%H:%M')} (Europe/Paris).
Opening hours: {RESTAURANT['hours']['en']}

VOICE STYLE
- Your words are converted to speech: no markdown, no lists, no emoji, no symbols like * or #.
- Keep every reply short: one or two sentences, and ask one question at a time.
- {PRICE_RULES[lang]}
- Dish names: use the name in the customer's language from the menu. Do not read the whole menu aloud; suggest two or three dishes when asked.

TAKEAWAY ORDERS
- Every change to the order MUST go through tools: add_to_cart, remove_from_cart. Never pretend an item was added.
- When you call a tool, call it straight away without saying anything first; speak once, after the tool result. Add several dishes in one turn by calling add_to_cart for each, then give a single short confirmation.
- If a request matches several dishes or none, ask the customer to choose. Only dishes from the menu exist.
- Galettes are savoury buckwheat pancakes (naturally gluten-free); crêpes are sweet wheat pancakes. Explain this briefly if the customer seems unsure.
- For the galette complète, ask whether they want the egg sunny-side up (miroir) or scrambled (brouillé). For cider, ask brut (dry) or doux (sweet). Put the answer in the note.
- When the customer is done, call view_cart, read back the items and the total, then ask for the name, phone number and pickup time.
- Pickup time must be during opening hours, at least 20 minutes from now.
- Only after the customer explicitly confirms the full recap, call place_order.

PAYMENT
{payment_rules(lang)}

TABLE RESERVATIONS
- Collect party size, date and time, then call check_availability. Bookable slots are every 30 minutes, 12:00-14:00 and 19:00-22:00, closed on Monday, max {MAX_COVERS_PER_SLOT} guests per slot.
- If the slot is full, offer the alternatives returned by the tool.
- Then collect name and phone, read back the booking, and after the customer confirms call create_reservation.

OTHER
- Repeat phone numbers back digit by digit (in French, by pairs).
- If the customer asks for a human, says they want to complain, or you fail to understand twice, apologise and say a staff member will call them back.
- After an order or reservation is confirmed, give the order / reservation number, thank the customer and say goodbye.

MENU (id | French | English | Chinese | price)
{menu_for_prompt()}
"""


TOOLS = ToolsSchema(
    standard_tools=[
        FunctionSchema(
            name="add_to_cart",
            description="Add a dish to the customer's takeaway order.",
            properties={
                "item_id": {"type": "string", "enum": list(MENU_BY_ID), "description": "Dish id from the menu."},
                "quantity": {"type": "integer", "minimum": 1, "description": "Number of portions."},
                "note": {"type": "string", "description": "Optional note, e.g. egg style, cider brut/doux, or 'sans lardons'."},
            },
            required=["item_id", "quantity"],
        ),
        FunctionSchema(
            name="remove_from_cart",
            description="Remove a dish (or some portions of it) from the order.",
            properties={
                "item_id": {"type": "string", "enum": list(MENU_BY_ID)},
                "quantity": {"type": "integer", "minimum": 1, "description": "Portions to remove; omit to remove the dish entirely."},
            },
            required=["item_id"],
        ),
        FunctionSchema(
            name="view_cart",
            description="Get the current order lines and total, to read them back to the customer.",
            properties={},
            required=[],
        ),
        FunctionSchema(
            name="place_order",
            description="Submit the takeaway order to the kitchen. Only call after the customer confirmed the full recap.",
            properties={
                "customer_name": {"type": "string"},
                "phone": {"type": "string", "description": "Digits only."},
                "pickup_time": {"type": "string", "description": "HH:MM, today."},
                "customer_confirmed": {"type": "boolean", "description": "True only if the customer explicitly confirmed the recap."},
                "payment": {"type": "string", "enum": ["pay_now", "pay_at_pickup"], "description": "pay_now = secure online payment link shown on the customer's screen; pay_at_pickup = pay at the counter."},
            },
            required=["customer_name", "phone", "pickup_time", "customer_confirmed"],
        ),
        FunctionSchema(
            name="check_availability",
            description="Check if a table is available for a party at a given date and time.",
            properties={
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "HH:MM"},
                "party_size": {"type": "integer", "minimum": 1, "maximum": 12},
            },
            required=["date", "time", "party_size"],
        ),
        FunctionSchema(
            name="create_reservation",
            description="Book the table. Only call after check_availability succeeded and the customer confirmed.",
            properties={
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "HH:MM"},
                "party_size": {"type": "integer", "minimum": 1, "maximum": 12},
                "customer_name": {"type": "string"},
                "phone": {"type": "string"},
            },
            required=["date", "time", "party_size", "customer_name", "phone"],
        ),
    ]
)


def speech_units(text: str, lang: str) -> list[str]:
    """Words for fr/en; single characters for Chinese (no spaces between words)."""
    if lang == "zh":
        return re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+", text.lower())
    return re.findall(r"[\w']+", text.lower())


class EchoGuard:
    """Remembers what the bot just said, to recognise its own voice coming back through the mic.

    On speakerphones the bot's audio leaks into the caller's microphone; the browser's echo
    cancellation removes most of it but not all, and the leftover gets transcribed ("Bonjour.")
    and used to interrupt the bot. A transcript made while the bot talks, or just after, that
    consists mostly of the bot's own recent words is treated as echo.
    """

    TAIL_SECS = 1.0        # echo can still arrive this long after the bot stops

    def __init__(self, lang: str):
        self.lang = lang
        self.bot_speaking = False
        self.stopped_at = 0.0
        self._recent: list[str] = []  # bot texts of the current and previous response

    def add_bot_text(self, text: str, new_response: bool = False):
        if new_response or not self._recent:
            self._recent = (self._recent[-1:] if self._recent else []) + [""]
        self._recent[-1] += text

    def strip_echo(self, text: str) -> str | None:
        """Return what the caller said with the bot's echoed words removed, or None if it's only echo.

        The recogniser often merges echo and real speech into one phrase ("bonjour et degemer mat
        au restaurant ... excusez-moi je voudrais une table ..."), so the echo is located as runs of
        consecutive words (Chinese: characters) that also appear in that order in what the bot just
        said. What is left over is the caller's own speech.
        """
        if not self.bot_speaking and time.monotonic() - self.stopped_at > self.TAIL_SECS:
            return text
        units = speech_units(text, self.lang)
        if not units:
            return None
        said = speech_units(" ".join(self._recent), self.lang)
        min_run = 2
        echoed: set[int] = set()
        for blk in SequenceMatcher(None, units, said, autojunk=False).get_matching_blocks():
            if blk.size >= min_run:
                echoed.update(range(blk.a, blk.a + blk.size))
        # Misheard echo words ("degemer" -> "dejemaymat") still sound like something the bot said.
        said_set = set(said)
        def sounds_said(u: str) -> bool:
            # Only while the bot talks: right after, callers often answer with the bot's own words.
            return self.bot_speaking and len(u) > 3 and any(SequenceMatcher(None, u, w).ratio() >= 0.7 for w in said_set)
        # Numbers are written differently by the voice and the recogniser ("quatre" vs "4",
        # "十三点五" vs "13.5"), so they never decide whether something is echo.
        def neutral(u: str) -> bool:
            return u.replace(".", "").isdigit() or (self.lang == "zh" and u in "零一二两三四五六七八九十百点")
        own = [i for i in range(len(units)) if i not in echoed and not sounds_said(units[i]) and not neutral(units[i])]
        # A lone leftover word between echoed runs is usually a misheard echo word: keep the caller's
        # speech as runs of 2+ consecutive own words (or everything, once the bot has stopped).
        if self.bot_speaking:
            own_set = set(own)
            own = [i for i in own if i - 1 in own_set or i + 1 in own_set]
        # While the bot talks, a few stray words are more likely echo or noise than an interruption.
        needed = (4 if self.lang == "zh" else 3) if self.bot_speaking else 1
        if len(own) < needed:
            return None
        if not self.bot_speaking:
            # Just after the bot stopped: a phrase made almost only of the bot's words is its echo
            # finishing late. Anything with some words of the caller's own is kept unchanged, since
            # callers often answer with the bot's own words ("我要经典荞麦饼").
            return None if len(own) / len(units) < (0.25 if self.lang == "zh" else 0.3) else text
        kept = units[min(own): max(own) + 1]
        if len(kept) == len(units):
            return text
        return ("" if self.lang == "zh" else " ").join(kept)


class EchoFilter(FrameProcessor):
    """Sits right after STT: drops transcripts that are the bot's own echo, relays the rest's interim text to the page."""

    def __init__(self, guard: EchoGuard):
        super().__init__()
        self._guard = guard

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, BotStartedSpeakingFrame):
            self._guard.bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._guard.bot_speaking = False
            self._guard.stopped_at = time.monotonic()
        elif isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)) and direction == FrameDirection.DOWNSTREAM:
            own_words = self._guard.strip_echo(frame.text)
            if own_words is None:
                logger.debug(f"Echo ignored: {frame.text!r}")
                return
            if own_words != frame.text:
                logger.debug(f"Echo stripped: {frame.text!r} -> {own_words!r}")
                frame.text = own_words
            if isinstance(frame, InterimTranscriptionFrame):
                await self.push_frame(OutputTransportMessageUrgentFrame(message={"type": "user_interim", "text": frame.text}))
        await self.push_frame(frame, direction)


class LangMinWordsUserTurnStart(MinWordsUserTurnStartStrategy):
    """Barge-in needs real words: while the bot talks, min_words words (Chinese: min_words + 1
    characters); otherwise one word starts the turn. Noise, coughs and echo alone never cut the bot off."""

    def __init__(self, *, lang: str, min_words: int, **kwargs):
        super().__init__(min_words=min_words, **kwargs)
        self._lang = lang

    async def _handle_transcription(self, frame):
        needed = (self._min_words + (1 if self._lang == "zh" else 0)) if self._bot_speaking else 1
        if len(speech_units(frame.text, self._lang)) >= needed:
            await self.trigger_user_turn_started()
            return ProcessFrameResult.STOP
        return ProcessFrameResult.CONTINUE


class TranscriptRelay(FrameProcessor):
    """Forwards what the user said and what the bot says to the web page."""

    def __init__(self, role: str, guard: EchoGuard | None = None):
        super().__init__()
        self._role = role
        self._guard = guard

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        message = None
        if self._role == "user" and isinstance(frame, TranscriptionFrame):
            message = {"type": "user", "text": frame.text}
        elif self._role == "bot" and isinstance(frame, LLMFullResponseStartFrame):
            message = {"type": "bot_start"}
            if self._guard:
                self._guard.add_bot_text("", new_response=True)
        elif self._role == "bot" and isinstance(frame, LLMTextFrame):
            message = {"type": "bot_delta", "text": frame.text}
            if self._guard:
                self._guard.add_bot_text(frame.text)
        elif self._role == "bot" and isinstance(frame, LLMFullResponseEndFrame):
            message = {"type": "bot_end"}
        await self.push_frame(frame, direction)
        if message:
            await self.push_frame(OutputTransportMessageUrgentFrame(message=message))


class CallStatusObserver(BaseObserver):
    """Tells the page what the bot hears and does, so callers can see the line works.

    Sends: the input level the server receives (a few times per second), interim
    transcripts, and state changes: user speaking, thinking, bot speaking.
    """

    LEVEL_INTERVAL = 0.2

    def __init__(self):
        super().__init__(observe_every_push=False)
        self.task: PipelineTask | None = None
        self._last_level = 0.0
        self._state = ""

    async def _set_state(self, state: str):
        # Speaking frames are broadcast in both directions, so the same change arrives twice.
        if state != self._state:
            self._state = state
            await self._send({"type": "state", "state": state})

    async def _send(self, message: dict):
        if self.task:
            await self.task.queue_frame(OutputTransportMessageUrgentFrame(message=message))

    async def on_push_frame(self, data: FramePushed):
        frame = data.frame
        if isinstance(frame, InputAudioRawFrame):
            now = time.monotonic()
            if now - self._last_level >= self.LEVEL_INTERVAL:
                self._last_level = now
                samples = np.frombuffer(frame.audio, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples**2))) / 32768 if samples.size else 0.0
                await self._send({"type": "heard_level", "level": round(min(1.0, rms * 8), 3)})
        elif isinstance(frame, UserStartedSpeakingFrame):
            await self._set_state("user_speaking")
        elif isinstance(frame, UserStoppedSpeakingFrame):
            await self._set_state("thinking")
        elif isinstance(frame, FunctionCallsStartedFrame):
            await self._set_state("thinking")
        elif isinstance(frame, BotStartedSpeakingFrame):
            await self._set_state("bot_speaking")
        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self._set_state("listening")


async def run_bot(connection: SmallWebRTCConnection, lang: str, origin: str = "http://localhost:7860"):
    if lang not in LANG_NAMES:
        lang = "fr"
    logger.info(f"New call, language={lang}, providers={providers.selected()}")

    cart = Cart()
    echo_guard = EchoGuard(lang)
    echo_guard.add_bot_text(GREETINGS[lang])
    waiting_payment: list[str] = []  # order ids this call registered a payment listener for
    task: PipelineTask | None = None

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    stt = providers.build_stt(lang)
    tts = providers.build_tts(lang)
    llm = providers.build_llm()

    async def notify(message: dict):
        await llm.push_frame(OutputTransportMessageUrgentFrame(message=message))

    async def add_to_cart(params: FunctionCallParams):
        args = params.arguments
        item_id, quantity = args.get("item_id"), int(args.get("quantity", 1))
        if item_id not in MENU_BY_ID:
            await params.result_callback({"ok": False, "error": "unknown_item"})
            return
        cart.add(item_id, quantity, args.get("note", "") or "")
        await notify({"type": "cart", "cart": cart.to_dict(lang)})
        await params.result_callback({"ok": True, "cart": cart.to_dict(lang)})

    async def remove_from_cart(params: FunctionCallParams):
        args = params.arguments
        removed = cart.remove(args.get("item_id"), args.get("quantity"))
        await notify({"type": "cart", "cart": cart.to_dict(lang)})
        await params.result_callback({"ok": removed, "cart": cart.to_dict(lang)})

    async def view_cart(params: FunctionCallParams):
        await params.result_callback(cart.to_dict(lang))

    async def place_order(params: FunctionCallParams):
        args = params.arguments
        if not args.get("customer_confirmed"):
            await params.result_callback({"ok": False, "error": "read the recap and get explicit confirmation first"})
            return
        if not cart.lines:
            await params.result_callback({"ok": False, "error": "cart_is_empty"})
            return
        pay_now = payments.enabled() and args.get("payment") == "pay_now"
        order = store.add_order(
            {
                "customer_name": args.get("customer_name", ""),
                "phone": args.get("phone", ""),
                "pickup_time": args.get("pickup_time", ""),
                "language": lang,
                "payment": "pending" if pay_now else "pay_at_pickup",
                **cart.to_dict(lang),
            }
        )
        cart.lines.clear()
        result = {"ok": True, "order_id": order["id"], "total": order["total"], "pickup_time": order["pickup_time"], "payment": order["payment"]}
        if pay_now:
            try:
                checkout = await payments.create_checkout(order, origin)
                order = store.update_order(order["id"], payment_session_id=checkout["id"], payment_url=checkout["url"])
                payments.payment_listeners[order["id"]] = on_paid
                waiting_payment.append(order["id"])
                await notify({"type": "payment_link", "url": checkout["url"], "amount": order["total"], "order_id": order["id"]})
                result["payment"] = "pay_button_shown_on_screen"
            except Exception as e:
                logger.error(f"Stripe checkout failed for {order['id']}: {e}")
                order = store.update_order(order["id"], payment="pay_at_pickup")
                result.update(payment="pay_at_pickup", payment_fallback="online payment unavailable")
        await notify({"type": "order_placed", "order": order})
        await params.result_callback(result)

    async def on_paid(order: dict):
        await notify({"type": "payment_status", "order": order})
        if task:
            await task.queue_frame(
                LLMMessagesAppendFrame(
                    messages=[{"role": "user", "content": f"[System notice, not said by the customer] Payment received for order {order['id']} ({order['total']} EUR). Thank the customer briefly."}],
                    run_llm=True,
                )
            )

    async def check_availability(params: FunctionCallParams):
        args = params.arguments
        parsed = parse_slot(args.get("date", ""), args.get("time", ""))
        if isinstance(parsed, str):
            await params.result_callback({"available": False, "reason": parsed})
            return
        day, slot = parsed
        party = int(args.get("party_size", 2))
        available = store.covers_booked(day, slot) + party <= MAX_COVERS_PER_SLOT
        result = {"available": available, "date": day.isoformat(), "time": slot.strftime("%H:%M")}
        if not available:
            result["alternatives_same_day"] = nearby_free_slots(day, slot, party)
        await params.result_callback(result)

    async def create_reservation(params: FunctionCallParams):
        args = params.arguments
        parsed = parse_slot(args.get("date", ""), args.get("time", ""))
        if isinstance(parsed, str):
            await params.result_callback({"ok": False, "reason": parsed})
            return
        day, slot = parsed
        party = int(args.get("party_size", 2))
        if store.covers_booked(day, slot) + party > MAX_COVERS_PER_SLOT:
            await params.result_callback({"ok": False, "reason": "slot_full", "alternatives_same_day": nearby_free_slots(day, slot, party)})
            return
        reservation = store.add_reservation(
            {
                "date": day.isoformat(),
                "time": slot.strftime("%H:%M"),
                "party_size": party,
                "customer_name": args.get("customer_name", ""),
                "phone": args.get("phone", ""),
                "language": lang,
            }
        )
        await notify({"type": "reservation", "reservation": reservation})
        await params.result_callback({"ok": True, "reservation_id": reservation["id"]})

    for name, handler in {
        "add_to_cart": add_to_cart,
        "remove_from_cart": remove_from_cart,
        "view_cart": view_cart,
        "place_order": place_order,
        "check_availability": check_availability,
        "create_reservation": create_reservation,
    }.items():
        llm.register_function(name, handler)

    context = LLMContext(
        messages=[
            {"role": "system", "content": system_prompt(lang)},
        ],
        tools=TOOLS,
    )
    aggregators = LLMContextAggregatorPair(
        context,
        # min_volume lowered from 0.6 so quiet laptop microphones still trigger speech detection.
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(min_volume=0.35)),
            # Turns start from transcribed words, not raw voice activity, so echo and noise can't interrupt the bot.
            user_turn_strategies=UserTurnStrategies(start=[LangMinWordsUserTurnStart(lang=lang, min_words=3)]),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            EchoFilter(echo_guard),
            TranscriptRelay("user"),
            aggregators.user(),
            llm,
            TranscriptRelay("bot", echo_guard),
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )
    status = CallStatusObserver()
    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True),
        enable_rtvi=False,
        idle_timeout_secs=180,
        observers=[status],
    )
    status.task = task

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await task.queue_frames(
            [
                OutputTransportMessageUrgentFrame(message={"type": "bot_start"}),
                OutputTransportMessageUrgentFrame(message={"type": "bot_delta", "text": GREETINGS[lang]}),
                OutputTransportMessageUrgentFrame(message={"type": "bot_end"}),
                TTSSpeakFrame(GREETINGS[lang]),
            ]
        )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Call ended by client")
        for order_id in waiting_payment:
            payments.payment_listeners.pop(order_id, None)
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.add_workers(task)
    await runner.run()

