from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
from urllib import request

from autos.paths import episode_dirs


@dataclass(frozen=True)
class SceneContext:
    """
    Minimal scene context passed to the scoring prompt.
    """

    scene_index: int
    duration_sec: float
    title: str
    caption: str
    dialogue: str


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def load_prompt(path: Path) -> str:
    """
    Load a prompt template from disk.
    """
    return path.read_text().strip()


def build_system_prompt(system_template: str, schema_json: str) -> str:
    """
    Inject the schema JSON into the system prompt template.
    """
    return system_template.replace("<SCHEMA_JSON>", schema_json.strip())


def build_user_prompt(template: str, context: SceneContext) -> str:
    """
    Render the user prompt for a single scene.
    """
    return template.format(
        scene_index=context.scene_index,
        duration_sec=f"{context.duration_sec:.2f}",
        title=context.title or "NONE",
        caption=context.caption or "NONE",
        dialogue=context.dialogue or "NONE",
    )


def _load_timeline(path: Path) -> List[Dict[str, Any]]:
    data = _load_json(path)
    return data.get("scenes", [])


def _load_vision(vision_root: Path) -> Dict[int, Dict[str, str]]:
    results: Dict[int, Dict[str, str]] = {}
    for scene_dir in sorted(vision_root.iterdir()):
        if not scene_dir.is_dir() or not scene_dir.name.startswith("scene_"):
            continue
        try:
            scene_index = int(scene_dir.name.split("_", 1)[1])
        except ValueError:
            continue
        title_path = scene_dir / "title.json"
        caption_path = scene_dir / "captions.json"
        title = ""
        caption = ""
        if caption_path.exists():
            caption = _load_json(caption_path).get("merged_caption", "")
        if title_path.exists():
            title = _load_json(title_path).get("title", "")
        results[scene_index] = {"title": title, "caption": caption}
    return results


def build_scene_contexts(
    *,
    timeline_scenes: Iterable[Dict[str, Any]],
    vision_lookup: Dict[int, Dict[str, str]],
    max_dialogue_chars: int,
    max_caption_chars: int,
    max_title_chars: int,
) -> List[SceneContext]:
    """
    Build prompt contexts from timeline + vision outputs.
    """
    contexts: List[SceneContext] = []
    for scene in timeline_scenes:
        scene_index = int(scene.get("scene_index", 0))
        duration = float(scene.get("duration_sec", 0.0))
        dialogues = scene.get("dialogues", [])
        dialogue_text = " ".join(d.get("text", "") for d in dialogues if d.get("text"))
        dialogue_text = _truncate(dialogue_text, max_dialogue_chars)

        vision = vision_lookup.get(scene_index, {})
        title = _truncate(vision.get("title", ""), max_title_chars)
        caption = _truncate(vision.get("caption", ""), max_caption_chars)

        contexts.append(
            SceneContext(
                scene_index=scene_index,
                duration_sec=duration,
                title=title,
                caption=caption,
                dialogue=dialogue_text,
            )
        )
    return contexts


def _ollama_generate(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    top_p: float,
    top_k: int,
    seed: int | None,
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        },
    }
    if seed is not None:
        payload["options"]["seed"] = seed

    req = request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as exc:  # pragma: no cover - network guard
        raise RuntimeError(
            "Failed to reach Ollama at http://localhost:11434. Is Ollama running?"
        ) from exc

    data = json.loads(raw)
    content = data.get("response", "")
    if isinstance(content, dict):
        return content
    return json.loads(content)


def _validate_scores(payload: Dict[str, Any]) -> Dict[str, int]:
    scores = payload.get("scores", {})
    required = ["hook", "clarity", "emotion", "action", "novelty", "dialogue", "visual"]
    for key in required:
        if key not in scores:
            raise ValueError(f"Missing score: {key}")
        val = int(scores[key])
        if val < 0 or val > 10:
            raise ValueError(f"Score out of range for {key}: {val}")
        scores[key] = val
    return scores


def _weighted_total(scores: Dict[str, int], weights: Dict[str, float]) -> float:
    total_weight = 0.0
    weighted = 0.0
    for key, value in scores.items():
        w = float(weights.get(key, 1.0))
        weighted += value * w
        total_weight += w
    if total_weight <= 0:
        return 0.0
    return weighted / total_weight


def run_scoring(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    model: str,
    system_prompt_path: Path,
    user_prompt_path: Path,
    schema_path: Path,
    temperature: float,
    top_p: float,
    top_k: int,
    seed: int | None,
    max_dialogue_chars: int,
    max_caption_chars: int,
    max_title_chars: int,
    weights: Dict[str, float],
    overwrite: bool = False,
    show_progress: bool = True,
) -> Path:
    """
    Score scenes using an Ollama LLM and write scores to artifacts/<series>/<episode>/scores/.
    """
    log = logging.getLogger("autos.scoring")
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    timeline_path = dirs["timeline"] / "timeline_base.json"
    if not timeline_path.exists():
        raise FileNotFoundError(
            f"timeline_base.json not found at {timeline_path}. Run timeline first."
        )

    system_template = load_prompt(system_prompt_path)
    user_template = load_prompt(user_prompt_path)
    schema_json = schema_path.read_text()
    system_prompt = build_system_prompt(system_template, schema_json)

    timeline_scenes = _load_timeline(timeline_path)
    vision_lookup = _load_vision(dirs["vision"]) if dirs["vision"].exists() else {}
    contexts = build_scene_contexts(
        timeline_scenes=timeline_scenes,
        vision_lookup=vision_lookup,
        max_dialogue_chars=max_dialogue_chars,
        max_caption_chars=max_caption_chars,
        max_title_chars=max_title_chars,
    )

    scores_root = dirs["scores"]
    results: List[Dict[str, Any]] = []

    log.info("Scoring %s scenes with model=%s", len(contexts), model)

    def _score_scene(context: SceneContext) -> None:
        scene_dir = scores_root / f"scene_{context.scene_index:04d}"
        score_path = scene_dir / "score.json"
        if score_path.exists() and not overwrite:
            data = _load_json(score_path)
            results.append(data)
            return

        user_prompt = build_user_prompt(user_template, context)
        payload = _ollama_generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            seed=seed,
        )

        scores = _validate_scores(payload)
        total_score = _weighted_total(scores, weights)

        record = {
            "scene_index": context.scene_index,
            "scores": scores,
            "rationale": str(payload.get("rationale", "")).strip(),
            "total_score": round(total_score, 4),
            "model": model,
            "prompt_paths": {
                "system": str(system_prompt_path),
                "user": str(user_prompt_path),
                "schema": str(schema_path),
            },
        }

        scene_dir.mkdir(parents=True, exist_ok=True)
        (scene_dir / "prompt.txt").write_text(user_prompt)
        (scene_dir / "raw_response.json").write_text(json.dumps(payload, indent=2))
        score_path.write_text(json.dumps(record, indent=2))
        results.append(record)

    if show_progress:
        from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn

        with Progress(
            TextColumn("[bold]Scoring[/bold]"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("scores", total=len(contexts))
            for context in contexts:
                _score_scene(context)
                progress.advance(task)
    else:
        for context in contexts:
            _score_scene(context)

    results.sort(key=lambda r: r["total_score"], reverse=True)

    scores_root.mkdir(parents=True, exist_ok=True)
    (scores_root / "scores.json").write_text(json.dumps(results, indent=2))

    csv_lines = ["scene_index,total_score,hook,clarity,emotion,action,novelty,dialogue,visual"]
    for row in results:
        s = row["scores"]
        csv_lines.append(
            f"{row['scene_index']},{row['total_score']},{s['hook']},{s['clarity']},"
            f"{s['emotion']},{s['action']},{s['novelty']},{s['dialogue']},{s['visual']}"
        )
    (scores_root / "scores.csv").write_text("\n".join(csv_lines) + "\n")

    return scores_root
