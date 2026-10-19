// Restaurant page + browser "IP call" to the AI ordering bot over WebRTC.

const I18N = {
  fr: {
    eyebrow: "Crêperie bretonne · Montparnasse", title: "Galettes, crêpes et cidre — commandez de vive voix",
    lead: "Appelez directement depuis votre navigateur : notre assistant IA prend votre commande à emporter ou réserve votre table. Degemer mat !",
    call: "Appeler pour commander", hint: "Autorisez le micro. Vous parlerez à un assistant IA.",
    menuTitle: "La carte", infoTitle: "Infos pratiques", kitchenLink: "Écran cuisine (démo) →",
    callTitle: "Appel avec l'assistant IA", mute: "Micro coupé ?", hangup: "Raccrocher",
    cartTitle: "Votre commande", total: "Total", empty: "Aucun plat pour l'instant",
    connecting: "Connexion…", connected: "En ligne — parlez librement", ended: "Appel terminé",
    muteOn: "Couper le micro", muteOff: "Réactiver le micro", you: "Vous", bot: "Assistant",
    orderOk: (o) => `Commande ${o.id} envoyée en cuisine — retrait à ${o.pickup_time}, total €${o.total.toFixed(2)}.`,
    resOk: (r) => `Réservation ${r.id} : ${r.party_size} pers. le ${r.date} à ${r.time}.`,
    payNow: (a) => `Payer €${a.toFixed(2)}`, paidLabel: "Payé ✓", payWaiting: "Page sécurisée Stripe — en attente du paiement…",
    payTest: "Mode test : carte 4242 4242 4242 4242, date future, CVC au choix.",
    bannerPaid: (o) => `Paiement reçu pour la commande ${o.order_id} — merci ! Vous pouvez fermer cet onglet.`,
    bannerPending: "Paiement en cours de vérification…", bannerCancel: "Paiement annulé. Vous pouvez réessayer ou payer au retrait.",
    payAtPickup: "Paiement au retrait",
    minimize: "Réduire", expand: "Agrandir", close: "Fermer",
    micLevel: "Votre micro", heardLevel: "Reçu par l'IA",
    st_connecting: "Connexion…", st_listening: "À l'écoute — parlez", st_user_speaking: "Je vous entends…", st_thinking: "Réflexion…", st_bot_speaking: "L'assistant parle", st_ended: "Appel terminé",
    warnNoMic: "Aucun son détecté sur votre micro. Vérifiez qu'il n'est pas coupé ou choisissez un autre micro dans la liste ci-dessus.",
    warnNotHeard: "Votre micro capte du son, mais il n'arrive pas à l'assistant. Raccrochez et rappelez.",
    micError: "Micro inaccessible. Vérifiez les autorisations du navigateur.",
  },
  en: {
    eyebrow: "Breton crêperie · Montparnasse", title: "Galettes, crêpes and cider — just say what you'd like",
    lead: "Call straight from your browser: our AI assistant takes your takeaway order or books your table. Degemer mat — welcome!",
    call: "Call to order", hint: "Allow the microphone. You will talk to an AI assistant.",
    menuTitle: "Menu", infoTitle: "Visit us", kitchenLink: "Kitchen screen (demo) →",
    callTitle: "Call with the AI assistant", mute: "Mute", hangup: "Hang up",
    cartTitle: "Your order", total: "Total", empty: "No dishes yet",
    connecting: "Connecting…", connected: "Connected — just talk", ended: "Call ended",
    muteOn: "Mute", muteOff: "Unmute", you: "You", bot: "Assistant",
    orderOk: (o) => `Order ${o.id} sent to the kitchen — pickup at ${o.pickup_time}, total €${o.total.toFixed(2)}.`,
    resOk: (r) => `Reservation ${r.id}: ${r.party_size} guests on ${r.date} at ${r.time}.`,
    payNow: (a) => `Pay €${a.toFixed(2)}`, paidLabel: "Paid ✓", payWaiting: "Secure Stripe page — waiting for payment…",
    payTest: "Test mode: card 4242 4242 4242 4242, any future date, any CVC.",
    bannerPaid: (o) => `Payment received for order ${o.order_id} — thank you! You can close this tab.`,
    bannerPending: "Checking your payment…", bannerCancel: "Payment cancelled. You can try again or pay at pickup.",
    payAtPickup: "Pay at pickup",
    minimize: "Minimize", expand: "Expand", close: "Close",
    micLevel: "Your mic", heardLevel: "Heard by AI",
    st_connecting: "Connecting…", st_listening: "Listening — go ahead", st_user_speaking: "I can hear you…", st_thinking: "Thinking…", st_bot_speaking: "Assistant speaking", st_ended: "Call ended",
    warnNoMic: "No sound from your microphone. Check it isn't muted, or pick another one from the microphone list above.",
    warnNotHeard: "Your microphone picks up sound but it isn't reaching the assistant. Hang up and call again.",
    micError: "Microphone unavailable. Check your browser permissions.",
  },
  zh: {
    eyebrow: "布列塔尼可丽饼餐厅 · 巴黎蒙帕纳斯", title: "荞麦饼、可丽饼、苹果酒，开口就能点",
    lead: "直接在浏览器里拨打：AI 助手帮您点外带餐或预订座位。Degemer mat，欢迎光临！",
    call: "语音点餐", hint: "请允许使用麦克风。接听您的是 AI 助手。",
    menuTitle: "菜单", infoTitle: "餐厅信息", kitchenLink: "后厨看板（演示）→",
    callTitle: "与 AI 助手通话中", mute: "静音", hangup: "挂断",
    cartTitle: "您的订单", total: "合计", empty: "还没有点菜",
    connecting: "正在连接…", connected: "已接通，请直接说话", ended: "通话已结束",
    muteOn: "静音", muteOff: "取消静音", you: "您", bot: "助手",
    orderOk: (o) => `订单 ${o.id} 已发送到后厨，${o.pickup_time} 取餐，合计 €${o.total.toFixed(2)}。`,
    resOk: (r) => `预订 ${r.id}：${r.date} ${r.time}，${r.party_size} 位。`,
    payNow: (a) => `支付 €${a.toFixed(2)}`, paidLabel: "已支付 ✓", payWaiting: "Stripe 安全支付页面，等待付款…",
    payTest: "测试模式：卡号 4242 4242 4242 4242，任意未来日期，任意 CVC。",
    bannerPaid: (o) => `订单 ${o.order_id} 已付款，谢谢！可以关闭这个页面了。`,
    bannerPending: "正在确认付款…", bannerCancel: "付款已取消。可以重新支付，或到店付款。",
    payAtPickup: "到店付款",
    minimize: "收起", expand: "展开", close: "关闭",
    micLevel: "您的麦克风", heardLevel: "AI 收到的声音",
    st_connecting: "正在连接…", st_listening: "正在听，请说话", st_user_speaking: "听到您在说话…", st_thinking: "正在思考…", st_bot_speaking: "AI 正在说话", st_ended: "通话已结束",
    warnNoMic: "没有检测到麦克风声音。请确认麦克风没有静音，或在上方的麦克风列表里换一个。",
    warnNotHeard: "您的麦克风有声音，但 AI 没有收到。请挂断后重新拨打。",
    micError: "无法使用麦克风，请检查浏览器权限。",
  },
};

let lang = "fr";
let iceServers = [{ urls: "stun:stun.l.google.com:19302" }];
let menuData = null;
let pc = null, micStream = null, botBubble = null;
let audioCtx = null, meterTimer = null, callState = "connecting", wakeLock = null;
let localLevel = 0, heardLevel = 0, lastLocalSound = 0, lastHeardSound = 0, connectedAt = 0;
let payment = null;          // {order_id, amount, url, status, timer} for the order being paid
let cartQty = {};            // item_id -> quantity, mirrored on the menu
let sheet = "half";          // phone bottom sheet detent: mini | half | full
const phone = matchMedia("(max-width: 640px)");

const $ = (id) => document.getElementById(id);
const t = (key) => I18N[lang][key];

function applyLang(next) {
  lang = next;
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const v = t(el.dataset.i18n);
    if (typeof v === "string") el.textContent = v;
  });
  document.querySelectorAll(".lang-switch button").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  setMuteLabel(Boolean(micStream && !micStream.getAudioTracks()[0].enabled));
  if (document.getElementById("statePill")) setState(callState);
  if (document.getElementById("payBox")) renderPayment();
  renderMenu();
}

async function loadMenu() {
  menuData = await (await fetch("/api/menu")).json();
  renderMenu();
}

function renderMenu() {
  if (!menuData) return;
  const { categories, items, restaurant } = menuData;
  $("address").textContent = restaurant.address;
  $("hours").textContent = restaurant.hours[lang];
  $("menu").innerHTML = Object.entries(categories).map(([cat, names]) => `
    <div class="category">
      <h3>${names[lang]}</h3>
      ${items.filter((d) => d.category === cat).map((d) => `
        <div class="dish" data-id="${d.id}">
          <div><div class="dish-name"><span class="cart-badge" hidden></span>${d[lang]}</div>
          ${lang !== "fr" ? `<div class="dish-sub">${d.fr}</div>` : ""}</div>
          <div class="price">€${d.price.toFixed(2)}</div>
        </div>`).join("")}
    </div>`).join("");
  markMenu();
}

// Highlight the dishes in the current order, so callers see on the menu what the AI added.
function markMenu() {
  document.querySelectorAll(".dish").forEach((el) => {
    const qty = cartQty[el.dataset.id] || 0;
    el.classList.toggle("in-cart", qty > 0);
    const badge = el.querySelector(".cart-badge");
    badge.hidden = !qty;
    badge.textContent = `×${qty}`;
  });
}

async function checkConfig() {
  try {
    const cfg = await (await fetch("/api/config")).json();
    iceServers = cfg.ice_servers;
    if (cfg.missing_keys.length) {
      $("configWarning").hidden = false;
      $("configWarning").textContent = `Demo not configured — missing in demo/.env: ${cfg.missing_keys.join(", ")}`;
    }
  } catch { /* server offline: the call attempt will show the error */ }
}

// ---------- call ----------

// Desktop: a floating card that can be minimized to its header.
// Phone: a non-modal bottom sheet with three detents (mini bar, half screen, full screen),
// so the menu stays visible and scrollable above it during the call.
function setMinimized(min) {
  if (phone.matches) return setSheet(min ? "mini" : "half");
  $("callPanel").classList.toggle("minimized", min);
  updateMinButton(min);
}

function updateMinButton(min) {
  $("minBtn").setAttribute("aria-label", t(min ? "expand" : "minimize"));
  $("minBtn").title = t(min ? "expand" : "minimize");
}

function sheetHeights() {
  const vh = window.innerHeight;
  return { half: Math.round(vh * 0.5), full: vh - 12 };
}

function setSheet(state) {
  sheet = state;
  const panel = $("callPanel");
  panel.classList.remove("sheet-mini", "sheet-half", "sheet-full");
  panel.classList.add(`sheet-${state}`);
  panel.classList.toggle("minimized", state === "mini");
  updateMinButton(state === "mini");
  layoutSheet();
}

function layoutSheet() {
  const panel = $("callPanel");
  if (!phone.matches || panel.hidden) {
    panel.style.height = "";
    document.body.style.paddingBottom = "";
    return;
  }
  panel.style.height = sheet === "mini" ? "" : `${sheetHeights()[sheet]}px`;
  // Leave room under the page so the end of the menu can scroll above the sheet.
  requestAnimationFrame(() => { document.body.style.paddingBottom = `${panel.offsetHeight}px`; });
  $("transcript").scrollTop = $("transcript").scrollHeight;
}

// Drag the handle or header bar to resize; release snaps to the nearest detent.
function enableSheetDrag() {
  const panel = $("callPanel");
  let startY = 0, startH = 0, dragging = false, moved = false, justDragged = false;
  const onDown = (e) => {
    if (!phone.matches || e.target.closest("button, select")) return;
    dragging = true; moved = false;
    startY = e.clientY; startH = panel.offsetHeight;
    panel.setPointerCapture(e.pointerId);
  };
  const onMove = (e) => {
    if (!dragging) return;
    const dy = e.clientY - startY;
    if (!moved && Math.abs(dy) < 6) return;
    if (!moved) {
      moved = true;
      panel.classList.add("dragging");
      if (sheet === "mini") panel.classList.remove("minimized", "sheet-mini"), panel.classList.add("sheet-half");
    }
    const h = Math.min(sheetHeights().full, Math.max(72, startH - dy));
    panel.style.height = `${h}px`;
  };
  const onUp = (e) => {
    if (!dragging) return;
    dragging = false;
    panel.classList.remove("dragging");
    if (!moved) return; // a tap: handled by the click listeners
    justDragged = true;
    setTimeout(() => { justDragged = false; }, 0);
    const h = panel.offsetHeight, { half, full } = sheetHeights(), dy = e.clientY - startY;
    let next;
    if (h < half * 0.6) next = "mini";
    else if (h > (half + full) / 2) next = "full";
    else next = "half";
    // A quick flick moves one step in its direction even if it didn't travel far.
    if (Math.abs(dy) > 40 && next === sheet) {
      const order = ["mini", "half", "full"], i = order.indexOf(sheet);
      next = order[Math.max(0, Math.min(2, i + (dy < 0 ? 1 : -1)))];
    }
    setSheet(next);
  };
  [".sheet-handle", ".call-head"].forEach((sel) => panel.querySelector(sel).addEventListener("pointerdown", onDown));
  panel.addEventListener("pointermove", onMove);
  panel.addEventListener("pointerup", onUp);
  panel.addEventListener("pointercancel", onUp);
  // Tapping the handle toggles half <-> full (or opens a mini bar).
  panel.querySelector(".sheet-handle").addEventListener("click", () => {
    if (!justDragged) setSheet(sheet === "half" ? "full" : "half");
  });
  panel.querySelector(".call-head").addEventListener("click", (e) => { if (justDragged) e.stopImmediatePropagation(); }, true);
  window.addEventListener("resize", () => {
    if (phone.matches) setSheet(sheet);
    else { panel.classList.remove("sheet-mini", "sheet-half", "sheet-full"); layoutSheet(); }
  });
}

// While a call is live the red button hangs up; once it has ended it closes the panel.
function setHangupMode(live) {
  const label = $("hangupBtn").querySelector(".btn-label");
  label.dataset.i18n = live ? "hangup" : "close";
  label.textContent = t(live ? "hangup" : "close");
  $("hangupBtn").classList.toggle("ended", !live);
  $("hangupBtn").setAttribute("aria-label", t(live ? "hangup" : "close"));
  $("muteBtn").hidden = !live;
}

// On phones the call buttons show only icons; the label stays for screen readers and wider screens.
function setMuteLabel(muted) {
  const text = muted ? t("muteOff") : t("muteOn");
  $("muteBtn").querySelector(".btn-label").textContent = text;
  $("muteBtn").setAttribute("aria-label", text);
  $("muteBtn").title = text;
  $("muteBtn").classList.toggle("muted", muted);
}

function setStatus(text) { $("callStatus").textContent = text; }

function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.innerHTML = `<span class="who">${role === "user" ? t("you") : t("bot")}</span><span class="text"></span>`;
  div.querySelector(".text").textContent = text;
  $("transcript").appendChild(div);
  $("transcript").scrollTop = $("transcript").scrollHeight;
  return div;
}

function renderCart(cart) {
  cartQty = {};
  cart.lines.forEach((l) => { cartQty[l.item_id] = (cartQty[l.item_id] || 0) + l.quantity; });
  markMenu();
  $("cartLines").innerHTML = cart.lines.length
    ? cart.lines.map((l) => `<li><span>${l.quantity} × ${l.name}${l.note ? ` <em>(${l.note})</em>` : ""}</span><span>€${l.line_total.toFixed(2)}</span></li>`).join("")
    : `<li class="muted">${t("empty")}</li>`;
  $("cartTotal").textContent = `€${cart.total.toFixed(2)}`;
}

// ---------- online payment (Stripe Checkout, opened in a new tab so the call stays up) ----------

function renderPayment() {
  if (!payment) { $("payBox").hidden = true; return; }
  $("payBox").hidden = false;
  const paid = payment.status === "paid";
  $("payBtn").href = payment.url;
  $("payBtn").classList.toggle("paid", paid);
  $("payBtn").textContent = paid ? t("paidLabel") : t("payNow")(payment.amount);
  $("payState").textContent = paid ? "" : `${t("payWaiting")} ${t("payTest")}`;
}

function startPayment(msg) {
  stopPaymentPolling();
  payment = { order_id: msg.order_id, amount: msg.amount, url: msg.url, status: "pending", started: Date.now() };
  renderPayment();
  // No webhook: ask the server (which asks Stripe) until the order is paid, for up to 20 minutes.
  payment.timer = setInterval(async () => {
    if (!payment || Date.now() - payment.started > 20 * 60 * 1000) return stopPaymentPolling();
    try {
      const r = await (await fetch(`/api/orders/${payment.order_id}/payment`)).json();
      if (r.payment === "paid") markPaid();
    } catch { /* keep polling */ }
  }, 3000);
}

function markPaid() {
  if (!payment) return;
  payment.status = "paid";
  stopPaymentPolling();
  renderPayment();
}

function stopPaymentPolling() {
  if (payment?.timer) clearInterval(payment.timer);
  if (payment) payment.timer = null;
}

// Stripe sends the payer back to /?paid=<session id> (or /?cancelled=<order id>) in the new tab.
async function handlePaymentReturn() {
  const params = new URLSearchParams(location.search);
  const banner = $("payBanner");
  if (params.get("paid")) {
    banner.hidden = false;
    banner.className = "pay-banner warn";
    banner.textContent = t("bannerPending");
    try {
      const r = await fetch(`/api/payment/confirm?session_id=${encodeURIComponent(params.get("paid"))}`);
      const o = await r.json();
      if (r.ok && o.payment === "paid") { banner.className = "pay-banner"; banner.textContent = t("bannerPaid")(o); }
    } catch { /* leave the pending text */ }
  } else if (params.get("cancelled")) {
    banner.hidden = false;
    banner.className = "pay-banner warn";
    banner.textContent = t("bannerCancel");
  } else return;
  params.delete("paid"); params.delete("cancelled");
  history.replaceState(null, "", `${location.pathname}${params.size ? `?${params}` : ""}`);
}

function showConfirmation(text) {
  $("confirmation").hidden = false;
  $("confirmation").textContent = text;
}

function onBotMessage(msg) {
  switch (msg.type) {
    case "user":
      botBubble = null;
      $("interim").textContent = "";
      addBubble("user", msg.text);
      break;
    case "user_interim":
      $("interim").textContent = msg.text;
      break;
    case "heard_level":
      heardLevel = msg.level;
      if (heardLevel > 0.05) lastHeardSound = Date.now();
      $("heardMeter").style.width = `${Math.round(heardLevel * 100)}%`;
      break;
    case "state":
      setState(msg.state);
      break;
    case "bot_start":
      botBubble = null;
      break;
    case "bot_delta":
      if (!botBubble) botBubble = addBubble("bot", "");
      botBubble.querySelector(".text").textContent += msg.text;
      $("transcript").scrollTop = $("transcript").scrollHeight;
      break;
    case "bot_end":
      botBubble = null;
      break;
    case "cart":
      renderCart(msg.cart);
      break;
    case "order_placed":
      renderCart({ lines: [], total: 0 });
      showConfirmation(`${t("orderOk")(msg.order)}${msg.order.payment === "pay_at_pickup" ? ` ${t("payAtPickup")}.` : ""}`);
      break;
    case "payment_link":
      startPayment(msg);
      break;
    case "payment_status":
      if (payment && msg.order.id === payment.order_id && msg.order.payment === "paid") markPaid();
      break;
    case "reservation":
      showConfirmation(t("resOk")(msg.reservation));
      break;
  }
}

function setState(state) {
  callState = state;
  $("statePill").dataset.state = state;
  $("stateText").textContent = t(`st_${state}`);
}

function startLocalMeter(stream) {
  stopLocalMeter();
  audioCtx = new AudioContext();
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  audioCtx.createMediaStreamSource(stream).connect(analyser);
  const data = new Float32Array(analyser.fftSize);
  meterTimer = setInterval(() => {
    analyser.getFloatTimeDomainData(data);
    let sum = 0;
    for (const v of data) sum += v * v;
    localLevel = Math.min(1, Math.sqrt(sum / data.length) * 8);
    const now = Date.now();
    if (localLevel > 0.05) lastLocalSound = now;
    $("micMeter").style.width = `${Math.round(localLevel * 100)}%`;
    checkVoice(now);
  }, 100);
}

function stopLocalMeter() {
  if (meterTimer) clearInterval(meterTimer);
  meterTimer = null;
  if (audioCtx) audioCtx.close();
  audioCtx = null;
  $("micMeter").style.width = "0";
  $("heardMeter").style.width = "0";
}

// Warn after a few seconds of silence: either the mic captures nothing, or it does but the server doesn't receive it.
function checkVoice(now) {
  if (!connectedAt || now - connectedAt < 6000 || callState === "bot_speaking") return;
  let warning = "";
  if (now - lastLocalSound > 6000) warning = t("warnNoMic");
  else if (now - lastLocalSound < 1500 && now - lastHeardSound > 4000) warning = t("warnNotHeard");
  $("voiceWarning").hidden = !warning;
  $("voiceWarning").textContent = warning;
}

async function listMics() {
  const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
  const current = micStream?.getAudioTracks()[0]?.getSettings().deviceId;
  $("micSelect").innerHTML = devices.map((d, i) =>
    `<option value="${d.deviceId}" ${d.deviceId === current ? "selected" : ""}>${d.label || `Micro ${i + 1}`}</option>`).join("");
}

async function getMic(deviceId) {
  return navigator.mediaDevices.getUserMedia({
    audio: { deviceId: deviceId ? { exact: deviceId } : undefined, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
}

async function switchMic(deviceId) {
  if (!micStream) return;
  const next = await getMic(deviceId);
  const track = next.getAudioTracks()[0];
  track.enabled = micStream.getAudioTracks()[0].enabled;
  const sender = pc?.getSenders().find((s) => s.track?.kind === "audio");
  if (sender) await sender.replaceTrack(track);
  micStream.getTracks().forEach((tr) => tr.stop());
  micStream = next;
  lastLocalSound = Date.now();
  startLocalMeter(micStream);
}

function waitForIce(peer) {
  if (peer.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => { if (peer.iceGatheringState === "complete") { peer.removeEventListener("icegatheringstatechange", done); resolve(); } };
    peer.addEventListener("icegatheringstatechange", done);
    setTimeout(resolve, 3000); // don't hang if a STUN server is slow
  });
}

async function startCall() {
  $("callPanel").hidden = false;
  cartQty = {};
  markMenu();
  if (phone.matches) setSheet("half"); else setMinimized(false);
  setHangupMode(true);
  $("transcript").innerHTML = "";
  $("confirmation").hidden = true;
  stopPaymentPolling();
  payment = null;
  renderPayment();
  renderCart({ lines: [], total: 0 });
  $("callBtn").disabled = true;
  $("voiceWarning").hidden = true;
  $("interim").textContent = "";
  connectedAt = 0;
  setStatus(t("connecting"));
  setState("connecting");
  // Keep the phone screen on during the call (ignored where unsupported).
  navigator.wakeLock?.request("screen").then((l) => { wakeLock = l; }).catch(() => {});
  // iOS Safari only plays audio started from a tap: start the (still empty) player now.
  $("botAudio").play().catch(() => {});

  try {
    micStream = await getMic($("micSelect").value || undefined);
    startLocalMeter(micStream);
    listMics();
  } catch {
    setStatus(t("micError"));
    $("callBtn").disabled = false;
    return;
  }

  pc = new RTCPeerConnection({ iceServers });
  pc.addTransceiver(micStream.getAudioTracks()[0], { direction: "sendrecv" });
  pc.ontrack = (e) => {
    $("botAudio").srcObject = e.streams[0] || new MediaStream([e.track]);
    $("botAudio").play().catch(() => {});
  };
  pc.onconnectionstatechange = () => {
    if (pc?.connectionState === "connected") {
      setStatus(t("connected"));
      connectedAt = lastLocalSound = lastHeardSound = Date.now();
    }
    if (["failed", "closed", "disconnected"].includes(pc?.connectionState)) endCall();
  };

  const channel = pc.createDataChannel("messages", { ordered: true });
  channel.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === "signalling") return; // Pipecat internal
      onBotMessage(msg);
    } catch { /* ignore non-JSON */ }
  };

  await pc.setLocalDescription(await pc.createOffer());
  await waitForIce(pc);

  const res = await fetch("/api/offer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type, request_data: { lang, origin: location.origin } }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    setStatus(err.detail || `Error ${res.status}`);
    endCall(false);
    return;
  }
  const answer = await res.json();
  await pc.setRemoteDescription({ sdp: answer.sdp, type: answer.type });
}

function endCall(updateStatus = true) {
  if (pc) { const p = pc; pc = null; p.close(); }
  if (micStream) { micStream.getTracks().forEach((tr) => tr.stop()); micStream = null; }
  stopLocalMeter();
  wakeLock?.release().catch(() => {});
  wakeLock = null;
  connectedAt = 0;
  $("voiceWarning").hidden = true;
  $("interim").textContent = "";
  setState("ended");
  setHangupMode(false);
  $("callBtn").disabled = false;
  if (updateStatus) setStatus(t("ended"));
}

function toggleMute() {
  if (!micStream) return;
  const track = micStream.getAudioTracks()[0];
  track.enabled = !track.enabled;
  setMuteLabel(!track.enabled);
}

document.querySelectorAll(".lang-switch button").forEach((b) => b.addEventListener("click", () => {
  if (!pc) applyLang(b.dataset.lang); // language is fixed for the duration of a call
}));
$("callBtn").addEventListener("click", startCall);
$("hangupBtn").addEventListener("click", () => {
  if (pc || micStream) endCall();
  else { stopPaymentPolling(); $("callPanel").hidden = true; layoutSheet(); }
});
$("minBtn").addEventListener("click", (e) => {
  e.stopPropagation();
  setMinimized(!$("callPanel").classList.contains("minimized"));
});
enableSheetDrag();
// Tapping the header bar of a minimized panel opens it again.
document.querySelector(".call-head").addEventListener("click", (e) => {
  if ($("callPanel").classList.contains("minimized") && !e.target.closest("button")) setMinimized(false);
});
$("muteBtn").addEventListener("click", toggleMute);
$("micSelect").addEventListener("change", (e) => switchMic(e.target.value).catch(() => setStatus(t("micError"))));

applyLang(new URLSearchParams(location.search).get("lang") || "fr");
loadMenu();
checkConfig();
handlePaymentReturn();
