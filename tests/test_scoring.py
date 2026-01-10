from __future__ import annotations

from autos.scoring import (
    SceneContext,
    build_user_prompt,
    build_system_prompt,
    _weighted_total,
    _validate_scores,
)


def test_build_system_prompt_inserts_schema() -> None:
    template = "Schema:\n<SCHEMA_JSON>"
    schema = '{"type":"object"}'
    rendered = build_system_prompt(template, schema)
    assert "type" in rendered


def test_build_user_prompt_renders_fields() -> None:
    template = "SCENE_INDEX: {scene_index}\nDURATION: {duration_sec}\nTITLE: {title}"
    ctx = SceneContext(
        scene_index=7, duration_sec=12.5, title="Test", caption="", dialogue=""
    )
    rendered = build_user_prompt(template, ctx)
    assert "SCENE_INDEX: 7" in rendered
    assert "DURATION: 12.50" in rendered


def test_weighted_total_averages() -> None:
    scores = {"hook": 10, "clarity": 0}
    weights = {"hook": 1, "clarity": 1}
    assert _weighted_total(scores, weights) == 5.0


def test_validate_scores_enforces_range() -> None:
    payload = {"scores": {"hook": 5, "clarity": 7, "emotion": 6, "action": 3, "novelty": 2, "dialogue": 4, "visual": 8}}
    scores = _validate_scores(payload)
    assert scores["hook"] == 5
