from functools import lru_cache
from time import monotonic

import requests
from langchain_openai import ChatOpenAI

from app.core import config

PROVIDERS = {
    "openrouter": {"label": "OpenRouter", "base_url": config.OPENROUTER_BASE_URL, "key": config.OPENROUTER_API_KEY},
    "groq": {"label": "Groq", "base_url": "https://api.groq.com/openai/v1", "key": config.GROQ_API_KEY},
    "gemini": {"label": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key": config.GEMINI_API_KEY},
    "nvidia": {"label": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1", "key": config.NVIDIA_API_KEY},
}

MODEL_BLOCK_TTL_SECONDS = 30 * 60
_MODEL_BLOCKS = {}

PROVIDER_EXCLUSIONS = {
    "groq": ("whisper", "guard", "embed", "tts", "speech", "orpheus", "audio"),
    "gemini": ("embedding", "tts", "audio", "lyria", "image", "nano-banana", "video", "transcribe", "robotics", "computer-use", "deep-research", "antigravity"),
    "nvidia": ("embed", "tts", "speech", "image", "video", "guard", "safety", "detector", "ising-calibration", "nvclip", "riva-translate"),
}


def provider_config(provider: str):
    return PROVIDERS.get(provider)


def is_provider_configured(provider: str) -> bool:
    item = provider_config(provider)
    return bool(item and item["key"])


def model_unavailable_reason(provider: str, model_id: str):
    key = (provider, model_id)
    blocked = _MODEL_BLOCKS.get(key)
    if not blocked:
        return None
    reason, blocked_at = blocked
    if monotonic() - blocked_at >= MODEL_BLOCK_TTL_SECONDS:
        _MODEL_BLOCKS.pop(key, None)
        return None
    return reason


def mark_model_unavailable(provider: str, model_id: str, error):
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    status_code = status_code or getattr(response, "status_code", None)
    message = str(error).lower()
    billing_terms = ("billing", "payment", "quota", "credit", "insufficient", "rate limit", "rate_limit", "exceeded", "unauthorized", "forbidden", "permission")
    if status_code in {401, 402, 403, 429} or any(term in message for term in billing_terms):
        reason = "Provider access, billing, or quota limit reached. Temporarily unavailable; retry later."
        _MODEL_BLOCKS[(provider, model_id)] = (reason, monotonic())
        return reason
    return None


def _research_fit(model_id: str, name: str, context_window=None):
    """Transparent catalogue heuristic; never presented as a measured benchmark."""
    lowered = f"{model_id} {name}".lower()
    context = int(context_window) if context_window else None

    if context and context >= 1_000_000:
        context_score, context_reason = 25, "Very large context window"
    elif context and context >= 500_000:
        context_score, context_reason = 23, "Large context window"
    elif context and context >= 256_000:
        context_score, context_reason = 21, "Strong context capacity"
    elif context and context >= 128_000:
        context_score, context_reason = 18, "Good context capacity"
    elif context and context >= 64_000:
        context_score, context_reason = 14, "Moderate context capacity"
    elif context:
        context_score, context_reason = 8, "Limited context capacity"
    else:
        context_score, context_reason = 10, "Context capacity not published"

    reasoning_terms = ("reason", "thinking", "deepseek", "nemotron", "gpt-oss", "qwq", "r1", "pro")
    if any(term in lowered for term in reasoning_terms):
        reasoning_score, reasoning_reason = 25, "Reasoning-oriented model family/name"
    elif any(term in lowered for term in ("large", "ultra", "70b", "120b", "550b", "31b")):
        reasoning_score, reasoning_reason = 20, "Larger-capacity model family/name"
    else:
        reasoning_score, reasoning_reason = 14, "General-purpose model; reasoning not independently measured"

    if any(term in lowered for term in ("120b", "550b", "ultra", "large", "70b", "31b")):
        capability_score, capability_reason = 25, "Large model/capacity signal"
    elif any(term in lowered for term in ("27b", "30b", "32b", "flash", "super")):
        capability_score, capability_reason = 20, "Mid-to-large or capable model-family signal"
    else:
        capability_score, capability_reason = 15, "Model scale is not clear from catalogue metadata"

    if any(term in lowered for term in ("flash", "fast", "lite", "lightning", "instant")):
        speed_score, speed_reason = 10, "Speed-oriented model variant"
    else:
        speed_score, speed_reason = 6, "No explicit speed-oriented variant signal"

    stability_score, stability_reason = 15, "No preview marker in model ID"
    if any(term in lowered for term in ("preview", "experimental", "exp")):
        stability_score, stability_reason = 8, "Preview/experimental model; availability may change"

    total = min(100, context_score + reasoning_score + capability_score + speed_score + stability_score)
    return {
        "fit_score": total,
        "ranking_breakdown": {
            "context": context_score,
            "reasoning_signal": reasoning_score,
            "capability_signal": capability_score,
            "speed_signal": speed_score,
            "stability_signal": stability_score,
        },
        "recommendation_reasons": [context_reason, reasoning_reason, capability_reason, speed_reason, stability_reason],
        "ranking_basis": "Heuristic based on provider metadata and model-name signals; not a measured quality benchmark.",
    }


def _dynamic_model(provider: str, model_id: str, name: str, context_window=None, note="Discovered from the provider's live model catalogue.", pricing=None):
    context = int(context_window) if context_window else None
    ranking = _research_fit(model_id, name or model_id, context)
    return {
        "id": model_id,
        "name": name or model_id,
        "provider": provider,
        "strengths": ["provider-listed candidate", "chat suitability filtered by model family"],
        "context_window": context,
        "tier": "discovered",
        **ranking,
        "fit_note": note,
        "pricing": pricing,
    }


@lru_cache(maxsize=1)
def _discover_provider_models():
    discovered = []
    headers_by_provider = {
        provider: {"Authorization": f"Bearer {details['key']}"} if details["key"] else {}
        for provider, details in PROVIDERS.items()
    }

    if PROVIDERS["openrouter"]["key"]:
        try:
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                params={"output_modalities": "text", "sort": "intelligence-high-to-low"},
                headers=headers_by_provider["openrouter"],
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json().get("data", []):
                pricing = item.get("pricing") or {}
                model_id = item.get("id", "")
                name = item.get("name", model_id)
                architecture = item.get("architecture") or {}
                output_modes = architecture.get("output_modalities") or []
                input_modes = architecture.get("input_modalities") or []
                lowered = f"{model_id} {name}".lower()
                non_text_terms = ("lyria", "audio", "music", "image", "video", "tts", "transcribe", "embedding")
                if not model_id or any(term in lowered for term in non_text_terms):
                    continue
                if output_modes and "text" not in output_modes:
                    continue
                if input_modes and "text" not in input_modes:
                    continue
                try:
                    is_free = float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0
                except (TypeError, ValueError):
                    is_free = False
                discovered.append(_dynamic_model(
                    "openrouter", model_id, name, item.get("context_length"),
                    "Text model returned by OpenRouter's live catalogue; pricing is shown from its catalogue metadata.",
                    pricing={"prompt": pricing.get("prompt"), "completion": pricing.get("completion"), "is_free": is_free},
                ))
        except (requests.RequestException, ValueError, TypeError, KeyError):
            pass

    if PROVIDERS["groq"]["key"]:
        try:
            response = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers=headers_by_provider["groq"],
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json().get("data", []):
                model_id = item.get("id", "")
                lowered = model_id.lower()
                if not model_id or any(term in lowered for term in PROVIDER_EXCLUSIONS["groq"]):
                    continue
                discovered.append(_dynamic_model(
                    "groq", model_id, model_id,
                    item.get("context_window") or item.get("context_length"),
                    "Listed by Groq. Free-tier rate limits and model availability depend on the account.",
                ))
        except (requests.RequestException, ValueError, TypeError, KeyError):
            pass

    if PROVIDERS["nvidia"]["key"]:
        try:
            response = requests.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers=headers_by_provider["nvidia"],
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json().get("data", []):
                model_id = item.get("id", "")
                lowered = model_id.lower()
                if not model_id or any(term in lowered for term in PROVIDER_EXCLUSIONS["nvidia"]):
                    continue
                discovered.append(_dynamic_model(
                    "nvidia", model_id, item.get("name") or model_id,
                    item.get("context_length") or item.get("context_window"),
                    "Listed by NVIDIA NIM. Check model entitlement, credits and rate limits in the NVIDIA account.",
                ))
        except (requests.RequestException, ValueError, TypeError, KeyError):
            pass

    if PROVIDERS["gemini"]["key"]:
        try:
            response = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers={"x-goog-api-key": PROVIDERS["gemini"]["key"]},
                params={"pageSize": 1000},
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json().get("models", []):
                methods = item.get("supportedGenerationMethods", [])
                model_id = item.get("name", "").removeprefix("models/")
                lowered = model_id.lower()
                if not model_id or (methods and "generateContent" not in methods):
                    continue
                if any(term in lowered for term in PROVIDER_EXCLUSIONS["gemini"]):
                    continue
                discovered.append(_dynamic_model(
                    "gemini", model_id, item.get("displayName") or model_id,
                    item.get("inputTokenLimit"),
                    "Listed by Gemini. Free-tier availability and quotas vary by model, region and project.",
                ))
        except (requests.RequestException, ValueError, TypeError, KeyError):
            pass

    unique = {}
    for item in discovered:
        unique[(item["provider"], item["id"])] = item
    return list(unique.values())


def _all_model_definitions():
    definitions = []
    for item in _discover_provider_models():
        definitions.append(item)
    if PROVIDERS["openrouter"]["key"] and not any(
        item["provider"] == "openrouter" and item["id"] == "openrouter/free" for item in definitions
    ):
        definitions.append({
            "id": "openrouter/free",
            "name": "OpenRouter Free Router",
            "provider": "openrouter",
            "strengths": ["free model routing", "model variety"],
            "context_window": None,
            "tier": "free-router",
            **_research_fit("openrouter/free", "OpenRouter Free Router"),
            "fit_note": "Routes to an available free model; the underlying model can change between requests.",
        })
    return definitions


def get_model_config(model_id: str):
    return next((item for item in _all_model_definitions() if item["id"] == model_id), None)


def get_chat_model(model_id: str | None = None):
    selected = get_model_config(model_id or "openrouter/free")
    if not selected:
        raise ValueError(f"Unknown model: {model_id}")
    blocked_reason = model_unavailable_reason(selected["provider"], selected["id"])
    if blocked_reason:
        raise RuntimeError(blocked_reason)
    provider = PROVIDERS[selected["provider"]]
    if not provider["key"]:
        env_name = {
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
        }[selected["provider"]]
        raise RuntimeError(f"{env_name} is not configured. Add it to your .env file and restart ResearchFlow.")
    return ChatOpenAI(
        model=selected["id"],
        api_key=provider["key"],
        base_url=provider["base_url"],
        temperature=0.2,
        timeout=90,
        max_retries=1,
    )


def _provider_cost_label(provider: str, model_id: str, pricing=None):
    if provider == "openrouter":
        if model_id == "openrouter/free":
            return "Free router; underlying model may change"
        if pricing and pricing.get("is_free"):
            return "Free pricing listed in OpenRouter catalogue"
        if pricing:
            return "Paid pricing listed in OpenRouter catalogue"
        return "Pricing not confirmed; provider may charge"
    if provider == "groq":
        return "Free quota may apply; paid usage depends on provider account"
    if provider == "gemini":
        return "Free or paid access depends on model and Google project billing tier"
    return "NVIDIA endpoint entitlement and pricing depend on account/model"


def list_models():
    result = []
    for item in _all_model_definitions():
        provider = PROVIDERS[item["provider"]]
        result.append({
            **item,
            "provider_name": provider["label"],
            "configured": bool(provider["key"]),
            "available": bool(provider["key"]) and not model_unavailable_reason(item["provider"], item["id"]),
            "availability_reason": model_unavailable_reason(item["provider"], item["id"]),
            "cost_label": _provider_cost_label(item["provider"], item["id"], item.get("pricing")),
            "access_label": "Temporarily unavailable after provider rejection" if model_unavailable_reason(item["provider"], item["id"]) else ("API key detected" if provider["key"] else "API key required"),
        })
    return sorted(result, key=lambda item: (-item["fit_score"], item.get("provider_name", item["provider"]), item.get("name", item["id"])))


def recommend_free_models(limit: int = 5):
    """Return only models explicitly listed at zero token price for safe defaults."""
    candidates = [
        item for item in list_models()
        if item.get("available", True)
        and item["provider"] == "openrouter"
        and (item["id"] == "openrouter/free" or (item.get("pricing") or {}).get("is_free") is True)
    ]
    return sorted(candidates, key=lambda item: -item["fit_score"])[:limit]


def recommend_models(limit: int = 5):
    """Recommend high-fit models while preferring provider diversity."""
    candidates = [item for item in list_models() if item.get("available", True)]
    if not candidates:
        return []
    selected = []
    seen_providers = set()
    for item in candidates:
        if item["provider"] not in seen_providers:
            selected.append(item)
            seen_providers.add(item["provider"])
            if len(selected) >= limit:
                return selected[:limit]
    selected_ids = {item["id"] for item in selected}
    for item in candidates:
        if item["id"] not in selected_ids:
            selected.append(item)
            if len(selected) >= limit:
                break
    return selected[:limit]
