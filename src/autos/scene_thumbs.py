from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Tuple

from scenedetect import FrameTimecode, open_video
from scenedetect.scene_manager import save_images  # ✅ correct for 0.6.x


def export_scene_thumbnails(
    *,
    video: Path,
    scene_list: List[Tuple[Any, Any]],
    out_dir: Path,
    limit_scenes: int | None = 200,
    num_images: int = 1,
    quality: int = 90,
    frame_margin: int = 1,
    show_progress: bool = True,
) -> Path:
    """
    Writes:
      scenes/thumbs/raw/scene_0001.jpg
      scenes/thumbs/raw/scene_0002.jpg
      ...

    Uses PySceneDetect save_images() from scenedetect.scene_manager. :contentReference[oaicite:3]{index=3}
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if limit_scenes is not None:
        scene_list = scene_list[:limit_scenes]

    video_stream = open_video(str(video))

    save_images(
        scene_list=scene_list,
        video=video_stream,                 # ✅ in 0.6 this is called `video` :contentReference[oaicite:4]{index=4}
        num_images=num_images,
        frame_margin=frame_margin,
        image_extension="jpg",
        encoder_param=quality,
        image_name_template="scene_$SCENE_NUMBER",
        output_dir=str(out_dir),
        show_progress=show_progress,
        threading=True,
    )

    return out_dir


def _load_scene_bounds(path: Path) -> List[Tuple[float, float]]:
    data = json.loads(path.read_text())
    bounds: List[Tuple[float, float]] = []
    for idx, row in enumerate(data, start=1):
        start_sec = float(row["start_sec"])
        end_sec = float(row.get("end_sec", start_sec + float(row.get("duration_sec", 0.0))))
        if end_sec < start_sec:
            end_sec = start_sec
        bounds.append((start_sec, end_sec))
    return bounds


def export_scene_thumbnails_from_json(
    *,
    video: Path,
    scenes_json: Path,
    out_dir: Path,
    limit_scenes: int | None = 200,
    num_images: int = 1,
    quality: int = 90,
    frame_margin: int = 1,
    show_progress: bool = True,
) -> Path:
    """
    Writes thumbnails using a scenes JSON list with start/end seconds.
    Intended for merged scenes outputs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    bounds = _load_scene_bounds(scenes_json)

    if limit_scenes is not None:
        bounds = bounds[:limit_scenes]

    video_stream = open_video(str(video))
    fps = getattr(video_stream, "frame_rate", None)
    if fps is None:
        fps = video_stream.frame_rate

    scene_list = [
        (FrameTimecode(timecode=start, fps=fps), FrameTimecode(timecode=end, fps=fps))
        for start, end in bounds
    ]

    save_images(
        scene_list=scene_list,
        video=video_stream,
        num_images=num_images,
        frame_margin=frame_margin,
        image_extension="jpg",
        encoder_param=quality,
        image_name_template="scene_$SCENE_NUMBER",
        output_dir=str(out_dir),
        show_progress=show_progress,
        threading=True,
    )

    return out_dir
