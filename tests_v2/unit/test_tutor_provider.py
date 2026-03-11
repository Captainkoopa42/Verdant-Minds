"""Unit tests for scaffold-aware tutor provider."""

from __future__ import annotations

from cultivation.providers.tutor import TutorProvider
from cultivation.schemas import ScaffoldContext


def _context() -> ScaffoldContext:
    return ScaffoldContext(
        total_nodes=42,
        emergent_count=7,
        basin_count=3,
        basin_emergent_distribution={"basin_0": 3, "basin_1": 2, "basin_2": 2},
        top_concepts=["identity", "ethics"],
        recent_emergents=["Emergent_identity_time"],
        earlier_share=1.0,
        cycle=12,
    )


def test_set_scaffold_context_updates_internal_state() -> None:
    provider = TutorProvider(backend="local")
    ctx = _context()
    provider.set_scaffold_context(ctx)

    assert provider._context == ctx
    prompt = provider._build_system_prompt()
    assert "Total concepts: 42" in prompt
    assert "Active basins: 3" in prompt
    assert "Scaffold earlier-share: 1.000" in prompt


def test_generate_uses_scaffold_aware_prompt(monkeypatch) -> None:
    provider = TutorProvider(backend="local")
    provider.set_scaffold_context(_context())
    captured: dict[str, str] = {}

    def _fake_call(system_prompt: str, user_prompt: str, *, seed: int | None = None) -> str:
        captured["system"] = system_prompt
        captured["user"] = user_prompt
        return "How can identity and ethics remain coherent when their constraints conflict?"

    monkeypatch.setattr(provider, "_call_llm", _fake_call)
    text = provider.generate("Discuss identity and ethics", seed=3)

    assert "identity" in captured["system"].lower()
    assert "base strategy prompt" in captured["user"].lower()
    assert text.endswith("?")
    assert provider.last_fallback is False


def test_generate_falls_back_when_llm_errors() -> None:
    provider = TutorProvider(backend="local")
    provider.set_scaffold_context(_context())

    def _boom(system_prompt: str, user_prompt: str, *, seed: int | None = None) -> str:
        raise RuntimeError("rate limited")

    provider._call_llm = _boom  # type: ignore[method-assign]
    result = provider.generate("identity paradox", seed=11)

    assert result
    assert provider.last_fallback is True
    assert provider.last_error is not None
