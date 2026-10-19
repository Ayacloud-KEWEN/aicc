"""Builds STT / TTS / LLM services from environment variables.

Default stack: Azure Speech (STT + TTS) + DeepSeek. Alternatives kept ready:
Deepgram (STT), ElevenLabs (TTS), Anthropic Claude (LLM). Switch with
STT_PROVIDER / TTS_PROVIDER / LLM_PROVIDER in .env.
"""

import os

from pipecat.transcriptions.language import Language

LANGS = {
    # demo language code -> per-provider settings
    "fr": {"azure_stt": Language.FR_FR, "azure_voice": "fr-FR-DeniseNeural", "deepgram": Language.FR, "eleven": "fr"},
    "en": {"azure_stt": Language.EN_US, "azure_voice": "en-US-JennyNeural", "deepgram": Language.EN, "eleven": "en"},
    "zh": {"azure_stt": Language.ZH_CN, "azure_voice": "zh-CN-XiaoxiaoNeural", "deepgram": Language.ZH, "eleven": "zh"},
}

REQUIRED_KEYS = {
    "stt": {"azure": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"], "deepgram": ["DEEPGRAM_API_KEY"]},
    "tts": {"azure": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"], "elevenlabs": ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]},
    "llm": {"deepseek": ["DEEPSEEK_API_KEY"], "anthropic": ["ANTHROPIC_API_KEY"]},
}


def selected() -> dict[str, str]:
    return {
        "stt": os.getenv("STT_PROVIDER", "azure").lower(),
        "tts": os.getenv("TTS_PROVIDER", "azure").lower(),
        "llm": os.getenv("LLM_PROVIDER", "deepseek").lower(),
    }


def missing_keys() -> list[str]:
    """Env vars the selected providers need but that are empty."""
    missing = []
    for kind, provider in selected().items():
        for key in REQUIRED_KEYS[kind].get(provider, [f"unknown {kind} provider '{provider}'"]):
            if not os.getenv(key) and key not in missing:
                missing.append(key)
    if os.getenv("PAYMENT_MODE", "pickup").lower() == "stripe" and not os.getenv("STRIPE_SECRET_KEY"):
        missing.append("STRIPE_SECRET_KEY")
    return missing


def build_stt(lang: str):
    provider = selected()["stt"]
    if provider == "deepgram":
        from pipecat.services.deepgram.stt import DeepgramSTTService

        # nova-3 has no Chinese model; fall back to nova-2 for zh.
        model = "nova-2-general" if lang == "zh" else "nova-3-general"
        return DeepgramSTTService(
            api_key=os.environ["DEEPGRAM_API_KEY"],
            settings=DeepgramSTTService.Settings(model=model, language=LANGS[lang]["deepgram"]),
        )
    from pipecat.services.azure.stt import AzureSTTService

    return AzureSTTService(
        api_key=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
        settings=AzureSTTService.Settings(language=LANGS[lang]["azure_stt"], profanity="raw"),
    )


def build_tts(lang: str):
    provider = selected()["tts"]
    if provider == "elevenlabs":
        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

        return ElevenLabsTTSService(
            api_key=os.environ["ELEVENLABS_API_KEY"],
            settings=ElevenLabsTTSService.Settings(
                voice=os.environ["ELEVENLABS_VOICE_ID"],
                model=os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5"),
                language=LANGS[lang]["eleven"],
            ),
        )
    from pipecat.services.azure.tts import AzureTTSService

    voice = os.getenv(f"AZURE_VOICE_{lang.upper()}", LANGS[lang]["azure_voice"])
    return AzureTTSService(
        api_key=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
        settings=AzureTTSService.Settings(voice=voice, language=LANGS[lang]["azure_stt"]),
    )


def build_llm():
    provider = selected()["llm"]
    if provider == "anthropic":
        from pipecat.services.anthropic.llm import AnthropicLLMService

        return AnthropicLLMService(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            settings=AnthropicLLMService.Settings(
                model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5"),
                max_tokens=600,
                enable_prompt_caching=True,
            ),
        )
    from pipecat.services.deepseek.llm import DeepSeekLLMService

    # Without DEEPSEEK_MODEL, Pipecat's default DeepSeek model is used (thinking disabled).
    model = os.getenv("DEEPSEEK_MODEL")
    return DeepSeekLLMService(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        settings=DeepSeekLLMService.Settings(model=model) if model else None,
    )
