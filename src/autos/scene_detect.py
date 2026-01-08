from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

from autos.paths import episode_dirs
from autos.scene_thumbs import export_scene_thumbnails


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scene_index", "start_sec", "end_sec", "duration_sec"])
        for r in rows:
            w.writerow([r["scene_index"], r["start_sec"], r["end_sec"], r["duration_sec"]])


def _write_json(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2))


def run_scene_detect(
    video: Path,
    series_id: str,
    episode_id: str,
    artifacts_root: str | Path,
    *,
    threshold: float = 27.0,
    show_progress: bool = False,
    export_thumbs: bool = False,
    thumbs_limit: int | None = 200,
    thumbs_num_images: int = 1,
    thumbs_quality: int = 90,
) -> Tuple[Path, Path]:
    """
    Detect scenes and write:
      artifacts/<series>/<episode>/scenes/raw/scenes.(csv|json)
    Also writes legacy outputs for backward compatibility:
      artifacts/<series>/<episode>/scenes/raw_scenes.(csv|json)

    Uses open_video() + SceneManager.detect_scenes(video) (no deprecated VideoManager). :contentReference[oaicite:1]{index=1}
    """
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    scenes_root = dirs["scenes"]

    # New structured output locations
    raw_dir = scenes_root / "raw"
    raw_csv = raw_dir / "scenes.csv"
    raw_json = raw_dir / "scenes.json"

    # Legacy output locations (keep your current behavior)
    legacy_csv = scenes_root / "raw_scenes.csv"
    legacy_json = scenes_root / "raw_scenes.json"

    # ---- New PySceneDetect API (no VideoManager) ----
    video_stream = open_video(str(video))  # recommended backend opener :contentReference[oaicite:2]{index=2}
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video_stream, show_progress=show_progress)  # :contentReference[oaicite:3]{index=3}
    scene_list = scene_manager.get_scene_list()

    rows: List[Dict[str, Any]] = []
    for i, (start_tc, end_tc) in enumerate(scene_list, start=1):
        start_sec = float(start_tc.get_seconds())
        end_sec = float(end_tc.get_seconds())
        rows.append(
            {
                "scene_index": i,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": max(0.0, end_sec - start_sec),
            }
        )

    # Write both structured + legacy
    _write_csv(raw_csv, rows)
    _write_json(raw_json, rows)
    _write_csv(legacy_csv, rows)
    _write_json(legacy_json, rows)

    # Optional thumbnail export (raw)
    if export_thumbs:
        export_scene_thumbnails(
            video=video,
            scene_list=scene_list,
            out_dir=scenes_root / "thumbs" / "raw",
            limit_scenes=thumbs_limit,
            num_images=thumbs_num_images,
            quality=thumbs_quality,
        )

    return legacy_csv, legacy_json
