from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from autos.paths import episode_dirs


@dataclass
class Scene:
    """
    A single scene boundary used for chunking.

    Scene indices are preserved from detection/merge outputs so chunks can
    reference the original scene list without renumbering.
    """

    scene_index: int
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def _load_scenes(path: Path) -> List[Scene]:
    rows = json.loads(path.read_text())
    scenes: List[Scene] = []
    for idx, row in enumerate(rows, start=1):
        start_sec = float(row["start_sec"])
        end_sec = float(row.get("end_sec", start_sec + float(row.get("duration_sec", 0.0))))
        if end_sec < start_sec:
            end_sec = start_sec
        scene_index = int(row.get("scene_index", idx))
        scenes.append(Scene(scene_index=scene_index, start_sec=start_sec, end_sec=end_sec))
    scenes.sort(key=lambda s: (s.start_sec, s.end_sec))
    return scenes


def load_scene_list(scenes_root: Path) -> List[Scene]:
    """
    Load scenes for chunking, preferring merged outputs and falling back to raw.

    Expected locations (first match wins):
    - scenes/merged/scenes.json
    - scenes/merged_scenes.json
    - scenes/raw/scenes.json
    - scenes/raw_scenes.json
    """
    candidates = [
        scenes_root / "merged" / "scenes.json",
        scenes_root / "merged_scenes.json",
        scenes_root / "raw" / "scenes.json",
        scenes_root / "raw_scenes.json",
    ]
    for path in candidates:
        if path.exists():
            return _load_scenes(path)
    raise FileNotFoundError(
        "No scenes found for chunking. Expected merged or raw scenes JSON in scenes/."
    )


def build_chunks(
    scenes: List[Scene],
    *,
    target_sec: float,
    tolerance_sec: float,
) -> List[Dict[str, Any]]:
    """
    Build chunk ranges using the Nearest Scene Boundary Rule.

    Rules:
    - Never split scenes; chunk boundaries land on scene ends.
    - Choose the boundary closest to target_sec within tolerance_sec.
    - If none fall within tolerance, choose the nearest boundary overall.
    - Deterministic output for identical inputs.
    """
    if not scenes:
        return []

    chunks: List[Dict[str, Any]] = []
    i = 0
    chunk_index = 0
    n = len(scenes)

    while i < n:
        chunk_start_sec = scenes[i].start_sec
        last_under_idx: int | None = None
        first_over_idx: int | None = None
        best_idx: int | None = None
        best_abs: float | None = None
        best_dur: float | None = None

        for j in range(i, n):
            duration = scenes[j].end_sec - chunk_start_sec
            if duration <= target_sec:
                last_under_idx = j
            if abs(duration - target_sec) <= tolerance_sec:
                abs_diff = abs(duration - target_sec)
                if (
                    best_abs is None
                    or abs_diff < best_abs
                    or (abs_diff == best_abs and duration < (best_dur or duration))
                ):
                    best_idx = j
                    best_abs = abs_diff
                    best_dur = duration
            if duration > target_sec + tolerance_sec:
                first_over_idx = j
                break

        if best_idx is not None:
            end_idx = best_idx
        elif first_over_idx is None:
            end_idx = n - 1
        elif last_under_idx is None:
            end_idx = first_over_idx
        else:
            dur_under = scenes[last_under_idx].end_sec - chunk_start_sec
            dur_over = scenes[first_over_idx].end_sec - chunk_start_sec
            if abs(target_sec - dur_under) <= abs(dur_over - target_sec):
                end_idx = last_under_idx
            else:
                end_idx = first_over_idx

        chunk_start_scene = scenes[i]
        chunk_end_scene = scenes[end_idx]
        chunk = {
            "chunk_index": chunk_index,
            "start_scene_index": chunk_start_scene.scene_index,
            "end_scene_index": chunk_end_scene.scene_index,
            "chunk_start_sec": chunk_start_scene.start_sec,
            "chunk_end_sec": chunk_end_scene.end_sec,
            "duration_sec": max(0.0, chunk_end_scene.end_sec - chunk_start_scene.start_sec),
            "scene_count": (end_idx - i) + 1,
        }
        chunks.append(chunk)
        chunk_index += 1
        i = end_idx + 1

    return chunks


def write_chunks(path: Path, chunks: List[Dict[str, Any]]) -> None:
    """
    Write chunks JSON with stable formatting.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chunks, indent=2))


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    """
    Load chunks JSON from disk.
    """
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")
    return json.loads(path.read_text())


def format_chunk_summary(chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Build one-line summaries for quick inspection.
    """
    lines: List[str] = []
    for chunk in chunks:
        idx = int(chunk.get("chunk_index", 0))
        start_scene = int(chunk.get("start_scene_index", 0))
        end_scene = int(chunk.get("end_scene_index", start_scene))
        start_sec = float(chunk.get("chunk_start_sec", 0.0))
        end_sec = float(chunk.get("chunk_end_sec", start_sec))
        duration = float(chunk.get("duration_sec", max(0.0, end_sec - start_sec)))
        scene_count = int(chunk.get("scene_count", max(1, end_scene - start_scene + 1)))
        lines.append(
            f"chunk {idx}: scenes {start_scene}-{end_scene} ({scene_count}) | "
            f"{start_sec:.2f}s-{end_sec:.2f}s ({duration:.2f}s)"
        )
    return lines


def run_chunking(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    target_sec: float,
    tolerance_sec: float,
) -> Path:
    """
    Load merged scenes, build chunks, and write chunks/chunks.json.
    """
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    scenes_root = dirs["scenes"]

    scenes = load_scene_list(scenes_root)
    chunks = build_chunks(scenes, target_sec=target_sec, tolerance_sec=tolerance_sec)

    out_path = dirs["chunks"] / "chunks.json"
    write_chunks(out_path, chunks)
    return out_path
