from app.graph import llm


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": [{"id": "test-reasoner-70b", "context_window": 131072}]}


def test_provider_catalogue_discovers_models_and_marks_key_ready(monkeypatch):
    monkeypatch.setitem(llm.PROVIDERS["groq"], "key", "test-key")
    monkeypatch.setattr(llm.requests, "get", lambda *args, **kwargs: FakeResponse())
    llm._discover_provider_models.cache_clear()
    try:
        models = llm.list_models()
        discovered = next(item for item in models if item["id"] == "test-reasoner-70b")
        assert discovered["provider"] == "groq"
        assert discovered["configured"] is True
        assert discovered["context_window"] == 131072
        assert discovered["fit_score"] > 70
    finally:
        llm._discover_provider_models.cache_clear()


def test_catalogue_contains_all_four_provider_families():
    models = llm.list_models()
    assert {"openrouter", "groq", "gemini", "nvidia"} <= {item["provider"] for item in models}

class FakeOpenRouterResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": [
            {
                "id": "google/lyria-3-pro-preview",
                "name": "Google Lyria Audio",
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["audio"]},
            },
            {
                "id": "google/gemma-4-31b-it:free",
                "name": "Gemma 4 31B Free",
                "context_length": 131072,
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
            {
                "id": "paid/model",
                "name": "Paid Model",
                "pricing": {"prompt": "0.1", "completion": "0.2"},
                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            },
        ]}


def test_openrouter_discovery_keeps_free_and_paid_text_models(monkeypatch):
    monkeypatch.setitem(llm.PROVIDERS["openrouter"], "key", "test-key")
    monkeypatch.setattr(llm.requests, "get", lambda *args, **kwargs: FakeOpenRouterResponse())
    llm._discover_provider_models.cache_clear()
    try:
        discovered = llm._discover_provider_models()
        openrouter_ids = {item["id"] for item in discovered if item["provider"] == "openrouter"}
        assert "google/gemma-4-31b-it:free" in openrouter_ids
        assert "google/lyria-3-pro-preview" not in openrouter_ids
        assert "paid/model" in openrouter_ids
        paid_model = next(item for item in discovered if item["id"] == "paid/model")
        assert paid_model["pricing"]["is_free"] is False
    finally:
        llm._discover_provider_models.cache_clear()


def test_safe_defaults_only_include_explicitly_free_openrouter_models(monkeypatch):
    monkeypatch.setattr(llm, "list_models", lambda: [
        {"id": "free-a", "provider": "openrouter", "available": True, "pricing": {"is_free": True}, "fit_score": 90},
        {"id": "paid-a", "provider": "openrouter", "available": True, "pricing": {"is_free": False}, "fit_score": 99},
        {"id": "free-tier-unknown", "provider": "groq", "available": True, "fit_score": 95},
        {"id": "blocked-free", "provider": "openrouter", "available": False, "pricing": {"is_free": True}, "fit_score": 92},
    ])

    defaults = llm.recommend_free_models(5)

    assert [item["id"] for item in defaults] == ["free-a"]


def test_provider_billing_or_quota_rejection_temporarily_blocks_model():
    class PaymentRequiredError(Exception):
        status_code = 402

    reason = llm.mark_model_unavailable("groq", "paid-model", PaymentRequiredError())
    try:
        assert reason and "billing" in reason.lower()
        assert llm.model_unavailable_reason("groq", "paid-model") == reason
    finally:
        llm._MODEL_BLOCKS.pop(("groq", "paid-model"), None)


def test_research_fit_uses_transparent_metadata_signals():
    strong = llm._research_fit("deepseek-r1-70b", "DeepSeek Reasoning 70B", 1_000_000)
    basic = llm._research_fit("small-chat", "Small Chat", 8_000)
    assert strong["fit_score"] > basic["fit_score"]
    assert strong["ranking_breakdown"]["context"] == 25
    assert "not a measured quality benchmark" in strong["ranking_basis"]


def test_recommender_prefers_provider_diversity(monkeypatch):
    models = [
        {"id": "groq-a", "provider": "groq", "fit_score": 99},
        {"id": "groq-b", "provider": "groq", "fit_score": 98},
        {"id": "gemini-a", "provider": "gemini", "fit_score": 95},
        {"id": "nvidia-a", "provider": "nvidia", "fit_score": 93},
        {"id": "openrouter-a", "provider": "openrouter", "fit_score": 91},
        {"id": "gemini-b", "provider": "gemini", "fit_score": 89},
    ]
    monkeypatch.setattr(llm, "list_models", lambda: models)
    recommended = llm.recommend_models(5)
    assert [item["provider"] for item in recommended[:4]] == [
        "groq", "gemini", "nvidia", "openrouter"
    ]
    assert len(recommended) == 5
    assert [item["fit_score"] for item in recommended[:4]] == sorted(
        [item["fit_score"] for item in recommended[:4]], reverse=True
    )
    assert recommended[4]["provider"] in {"groq", "gemini", "nvidia", "openrouter"}


def test_catalogue_excludes_non_chat_model_families():
    assert any("lyria" in term for term in llm.PROVIDER_EXCLUSIONS["gemini"])
    assert any("orpheus" in term for term in llm.PROVIDER_EXCLUSIONS["groq"])
    assert any("safety" in term for term in llm.PROVIDER_EXCLUSIONS["nvidia"])
