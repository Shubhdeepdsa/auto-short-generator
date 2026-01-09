from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from autos.paths import episode_dirs


@dataclass(frozen=True)
class CaptionResult:
    """
    Captions for a single scene.
    """

    scene_index: int
    frame_captions: List[Dict[str, Any]]
    merged_caption: str
    model_name: str
    device: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "model": self.model_name,
            "device": self.device,
            "frames": self.frame_captions,
            "merged_caption": self.merged_caption,
        }


@dataclass(frozen=True)
class TitleResult:
    """
    Title for a single scene.
    """

    scene_index: int
    title: str
    model_name: str
    device: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_index": self.scene_index,
            "title": self.title,
            "model": self.model_name,
            "device": self.device,
        }


def _require_vision_deps() -> Tuple[Any, Any, Any]:
    """
    Load heavy vision dependencies on demand.
    """
    try:
        import torch
        from PIL import Image
        from transformers import pipeline
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "Vision dependencies are missing. Install with: uv sync --extra vision"
        ) from exc
    return torch, Image, pipeline


def _select_device(device: str) -> str:
    """
    Resolve the device string to a supported backend.
    """
    torch, _, _ = _require_vision_deps()
    pref = device.lower()
    if pref not in {"auto", "cpu", "cuda", "mps"}:
        return "cpu"
    if pref != "auto":
        return pref
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _pipeline_device_arg(device: str) -> Any:
    """
    Convert a device string into a transformers pipeline device argument.
    """
    if device == "cuda":
        return 0
    if device == "cpu":
        return -1
    return device


def merge_captions(captions: Iterable[str]) -> str:
    """
    Merge multiple captions into a single, most descriptive caption.
    """
    items = [c.strip() for c in captions if c and c.strip()]
    if not items:
        return ""
    items.sort(key=lambda s: (len(s.split()), len(s)), reverse=True)
    return items[0]


def build_title_from_caption(caption: str, *, max_words: int) -> str:
    """
    Create a short, deterministic title from a caption.
    """
    text = caption.strip().strip(".")
    if not text:
        return ""
    words = text.split()
    title = " ".join(words[: max(1, int(max_words))])
    return title[:1].upper() + title[1:] if title else title


def _load_frame_paths(frames_root: Path) -> List[Tuple[int, List[Path]]]:
    """
    Load frame paths grouped by scene index.
    """
    scene_dirs = sorted([p for p in frames_root.iterdir() if p.is_dir()])
    results: List[Tuple[int, List[Path]]] = []
    for scene_dir in scene_dirs:
        name = scene_dir.name
        if not name.startswith("scene_"):
            continue
        try:
            scene_index = int(name.split("_", 1)[1])
        except ValueError:
            continue
        images = sorted(
            list(scene_dir.glob("*.jpg"))
            + list(scene_dir.glob("*.jpeg"))
            + list(scene_dir.glob("*.png"))
            + list(scene_dir.glob("*.webp"))
        )
        if images:
            results.append((scene_index, images))
    return results


def _caption_images(
    image_paths: List[Path],
    *,
    model_name: str,
    device: str,
    batch_size: int,
) -> List[str]:
    """
    Caption a list of images using a vision model.
    """
    torch, Image, pipeline = _require_vision_deps()
    device_name = _select_device(device)
    pipe = pipeline("image-to-text", model=model_name, device=_pipeline_device_arg(device_name))

    def _extract_caption(output: Any) -> str:
        if isinstance(output, dict):
            return output.get("generated_text") or output.get("caption") or ""
        if isinstance(output, list):
            for item in output:
                text = _extract_caption(item)
                if text:
                    return text
        return ""

    captions: List[str] = []
    for i in range(0, len(image_paths), max(1, int(batch_size))):
        batch = image_paths[i : i + max(1, int(batch_size))]
        images = [Image.open(p).convert("RGB") for p in batch]
        with torch.no_grad():
            outputs = pipe(images)
        for img in images:
            img.close()
        for out in outputs:
            captions.append(_extract_caption(out))
    return captions


def run_vision_captions(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    model_name: str,
    device: str,
    batch_size: int,
    overwrite: bool = False,
    show_progress: bool = True,
) -> Path:
    """
    Generate per-scene frame captions and write vision/scene_XXXX/captions.json.
    """
    log = logging.getLogger("autos.vision")
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    frames_root = dirs["frames"]
    vision_root = dirs["vision"]
    device_name = _select_device(device)

    frame_groups = _load_frame_paths(frames_root)
    if not frame_groups:
        raise FileNotFoundError(
            f"No frames found under {frames_root}. Run extract-frames first."
        )

    log.info("Vision captions: %s scenes, model=%s, device=%s", len(frame_groups), model_name, device_name)

    def _process_scene(scene_index: int, images: List[Path]) -> None:
        out_dir = vision_root / f"scene_{scene_index:04d}"
        out_path = out_dir / "captions.json"
        if out_path.exists() and not overwrite:
            return
        captions = _caption_images(
            images, model_name=model_name, device=device_name, batch_size=batch_size
        )
        frame_captions = [
            {"path": str(path), "caption": caption} for path, caption in zip(images, captions)
        ]
        merged = merge_captions(captions)
        result = CaptionResult(
            scene_index=scene_index,
            frame_captions=frame_captions,
            merged_caption=merged,
            model_name=model_name,
            device=device_name,
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result.to_dict(), indent=2))

    if show_progress:
        from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn

        with Progress(
            TextColumn("[bold]Captions[/bold]"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("captions", total=len(frame_groups))
            for scene_index, images in frame_groups:
                _process_scene(scene_index, images)
                progress.advance(task)
    else:
        for scene_index, images in frame_groups:
            _process_scene(scene_index, images)

    return vision_root


def _generate_titles_with_model(
    captions: List[str],
    *,
    model_name: str,
    device: str,
    temperature: float,
    max_words: int,
    batch_size: int,
) -> List[str]:
    """
    Generate titles using a text model.
    """
    torch, _, pipeline = _require_vision_deps()
    device_name = _select_device(device)
    pipe = pipeline("text2text-generation", model=model_name, device=_pipeline_device_arg(device_name))
    do_sample = temperature > 0
    max_new_tokens = max(8, int(max_words) + 4)

    titles: List[str] = []
    for i in range(0, len(captions), max(1, int(batch_size))):
        batch = captions[i : i + max(1, int(batch_size))]
        with torch.no_grad():
            outputs = pipe(
                batch,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
            )
        for out in outputs:
            text = out.get("generated_text") or ""
            titles.append(build_title_from_caption(text, max_words=max_words))
    return titles


def run_vision_titles(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    model_name: str | None,
    device: str,
    max_words: int,
    temperature: float,
    batch_size: int,
    overwrite: bool = False,
    show_progress: bool = True,
) -> Path:
    """
    Generate per-scene titles from captions and write vision/scene_XXXX/title.json.
    """
    log = logging.getLogger("autos.vision")
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    vision_root = dirs["vision"]
    device_name = _select_device(device)

    caption_paths = sorted(vision_root.rglob("captions.json"))
    if not caption_paths:
        raise FileNotFoundError("No captions.json found. Run vision-captions first.")

    captions: List[str] = []
    scene_indices: List[int] = []
    for path in caption_paths:
        data = json.loads(path.read_text())
        captions.append(data.get("merged_caption", ""))
        scene_indices.append(int(data.get("scene_index", 0)))

    if model_name:
        titles = _generate_titles_with_model(
            captions,
            model_name=model_name,
            device=device_name,
            temperature=temperature,
            max_words=max_words,
            batch_size=batch_size,
        )
        model_used = model_name
    else:
        titles = [build_title_from_caption(c, max_words=max_words) for c in captions]
        model_used = "heuristic"

    log.info("Vision titles: %s scenes, model=%s, device=%s", len(scene_indices), model_used, device_name)

    def _write_title(scene_index: int, title: str, caption_path: Path) -> None:
        out_dir = caption_path.parent
        out_path = out_dir / "title.json"
        if out_path.exists() and not overwrite:
            return
        result = TitleResult(
            scene_index=scene_index, title=title, model_name=model_used, device=device_name
        )
        out_path.write_text(json.dumps(result.to_dict(), indent=2))

    if show_progress:
        from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn

        with Progress(
            TextColumn("[bold]Titles[/bold]"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("titles", total=len(scene_indices))
            for scene_index, title, caption_path in zip(scene_indices, titles, caption_paths):
                _write_title(scene_index, title, caption_path)
                progress.advance(task)
    else:
        for scene_index, title, caption_path in zip(scene_indices, titles, caption_paths):
            _write_title(scene_index, title, caption_path)

    return vision_root
