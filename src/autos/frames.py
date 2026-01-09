from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from autos.chunker import Scene, load_scene_list
from autos.paths import episode_dirs


@dataclass(frozen=True)
class FrameSample:
    """
    A computed frame sample position inside a scene.
    """

    scene_index: int
    timestamp_sec: float
    label: str


def _parse_sample_points(raw: Iterable[float]) -> List[float]:
    """
    Normalize and sort sample points into [0, 1] range.
    """
    points = [float(p) for p in raw]
    points = [p for p in points if 0.0 <= p <= 1.0]
    if not points:
        return [0.5]
    return sorted(points)


def compute_sample_points(
    scene: Scene,
    *,
    sample_points: Iterable[float],
    min_scene_sec: float,
) -> List[FrameSample]:
    """
    Compute sample timestamps for a single scene.

    If the scene duration is below min_scene_sec, returns a single midpoint sample.
    Otherwise, returns samples at the requested normalized positions.
    """
    duration = scene.duration_sec
    if duration <= 0:
        return []

    points = _parse_sample_points(sample_points)
    if duration < min_scene_sec:
        points = [0.5]

    samples: List[FrameSample] = []
    for p in points:
        timestamp = scene.start_sec + (duration * p)
        label = f"{int(round(p * 100)):02d}"
        samples.append(FrameSample(scene_index=scene.scene_index, timestamp_sec=timestamp, label=label))
    return samples


def compute_scene_samples(
    scenes: Iterable[Scene],
    *,
    sample_points: Iterable[float],
    min_scene_sec: float,
) -> List[FrameSample]:
    """
    Compute frame samples for all scenes.
    """
    samples: List[FrameSample] = []
    for scene in scenes:
        samples.extend(
            compute_sample_points(scene, sample_points=sample_points, min_scene_sec=min_scene_sec)
        )
    return samples


def _build_ffmpeg_cmd(
    *,
    video: Path,
    timestamp_sec: float,
    output_path: Path,
    image_format: str,
    quality: int,
) -> List[str]:
    """
    Build the ffmpeg command for single-frame extraction.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp_sec:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
    ]

    fmt = image_format.lower()
    if fmt in {"jpg", "jpeg"}:
        q = max(2, min(31, int(quality)))
        cmd += ["-q:v", str(q)]
    elif fmt == "png":
        q = max(0, min(9, int(quality)))
        cmd += ["-compression_level", str(q)]

    cmd.append(str(output_path))
    return cmd


def extract_frame(
    *,
    video: Path,
    timestamp_sec: float,
    output_path: Path,
    image_format: str,
    quality: int,
) -> None:
    """
    Extract a single frame using ffmpeg.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_ffmpeg_cmd(
        video=video,
        timestamp_sec=timestamp_sec,
        output_path=output_path,
        image_format=image_format,
        quality=quality,
    )
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_frame_extraction(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    video: Path,
    sample_points: Iterable[float],
    min_scene_sec: float,
    image_format: str = "jpg",
    quality: int = 2,
) -> Path:
    """
    Extract per-scene frames into artifacts/<series>/<episode>/frames/<scene_index>/.

    This uses the merged scene list when available, and falls back to raw scenes.
    """
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    scenes = load_scene_list(dirs["scenes"])
    samples = compute_scene_samples(
        scenes, sample_points=sample_points, min_scene_sec=min_scene_sec
    )

    frames_root = dirs["frames"]
    fmt = image_format.lower()
    for sample in samples:
        scene_dir = frames_root / f"scene_{sample.scene_index:04d}"
        filename = f"frame_{sample.label}.{fmt}"
        output_path = scene_dir / filename
        extract_frame(
            video=video,
            timestamp_sec=sample.timestamp_sec,
            output_path=output_path,
            image_format=fmt,
            quality=quality,
        )

    return frames_root


def format_frames_summary(frames_root: Path) -> List[str]:
    """
    Summarize extracted frames per scene folder.
    """
    if not frames_root.exists():
        raise FileNotFoundError(f"Frames folder not found: {frames_root}")

    scene_dirs = sorted([p for p in frames_root.iterdir() if p.is_dir()])
    lines: List[str] = []
    total = 0
    for scene_dir in scene_dirs:
        images = list(scene_dir.glob("*.jpg")) + list(scene_dir.glob("*.png")) + list(
            scene_dir.glob("*.webp")
        )
        count = len(images)
        total += count
        lines.append(f"{scene_dir.name}: {count} frames")
    lines.append(f"total: {total} frames")
    return lines
