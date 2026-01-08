from __future__ import annotations
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from autos.paths import episode_dirs

@dataclass
class Scene:
    i: int
    start_sec: float
    end_sec: float

    @property
    def dur(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)

def merge_micro_scenes(
    scenes: List[Scene],
    min_scene_sec: float = 1.5,
    max_merge_chain: int = 8,
) -> List[Scene]:
    if not scenes:
        return []

    merged: List[Scene] = []
    chain = 0

    for sc in scenes:
        if not merged:
            merged.append(sc)
            continue

        if sc.dur < min_scene_sec:
            # Merge into previous scene
            merged[-1].end_sec = max(merged[-1].end_sec, sc.end_sec)
            chain += 1
            if chain >= max_merge_chain:
                # Force break: start a new scene to avoid endless glue
                merged.append(sc)
                chain = 0
        else:
            merged.append(sc)
            chain = 0

    # Re-index
    for idx, sc in enumerate(merged, start=1):
        sc.i = idx

    return merged


def _load_raw_scenes(scenes_root: Path) -> List[Scene]:
    candidates = [
        scenes_root / "raw" / "scenes.json",
        scenes_root / "raw_scenes.json",
    ]
    for path in candidates:
        if path.exists():
            raw = json.loads(path.read_text())
            scenes: List[Scene] = []
            for idx, row in enumerate(raw, start=1):
                start_sec = float(row["start_sec"])
                end_sec = float(row.get("end_sec", start_sec + float(row.get("duration_sec", 0.0))))
                scene_index = int(row.get("scene_index", idx))
                scenes.append(Scene(i=scene_index, start_sec=start_sec, end_sec=end_sec))
            return scenes
    raise FileNotFoundError("No raw scenes found (expected scenes/raw/scenes.json or scenes/raw_scenes.json).")


def _write_merged_json(path: Path, scenes: List[Scene]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "scene_index": sc.i,
            "start_sec": sc.start_sec,
            "end_sec": sc.end_sec,
            "duration_sec": sc.dur,
        }
        for sc in scenes
    ]
    path.write_text(json.dumps(payload, indent=2))


def _write_merged_csv(path: Path, scenes: List[Scene]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scene_index", "start_sec", "end_sec", "duration_sec"])
        for sc in scenes:
            w.writerow([sc.i, sc.start_sec, sc.end_sec, sc.dur])


def run_scene_merge(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    min_scene_sec: float = 1.5,
    max_merge_chain: int = 8,
) -> tuple[Path, Path]:
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    scenes_root = dirs["scenes"]

    raw_scenes = _load_raw_scenes(scenes_root)
    merged = merge_micro_scenes(
        raw_scenes,
        min_scene_sec=min_scene_sec,
        max_merge_chain=max_merge_chain,
    )

    merged_dir = scenes_root / "merged"
    structured_json = merged_dir / "scenes.json"
    structured_csv = merged_dir / "scenes.csv"
    legacy_json = scenes_root / "merged_scenes.json"
    legacy_csv = scenes_root / "merged_scenes.csv"

    _write_merged_json(structured_json, merged)
    _write_merged_csv(structured_csv, merged)
    _write_merged_json(legacy_json, merged)
    _write_merged_csv(legacy_csv, merged)

    return legacy_json, legacy_csv
