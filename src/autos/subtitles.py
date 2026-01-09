from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List

import srt

from autos.chunker import Scene, load_scene_list
from autos.paths import episode_dirs


@dataclass(frozen=True)
class SubtitleLine:
    """
    Normalized subtitle line with seconds-based timestamps.
    """

    index: int
    start_sec: float
    end_sec: float
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
        }


def _sec_to_timedelta(value: float) -> timedelta:
    return timedelta(seconds=float(value))


def parse_srt(path: Path, *, offset_ms: int = 0) -> List[SubtitleLine]:
    """
    Parse an .srt file into normalized subtitle lines.

    Args:
        path: Path to the .srt file.
        offset_ms: Optional time shift applied to all subtitles (positive or negative).

    Returns:
        List of SubtitleLine with seconds-based timestamps.
    """
    raw = path.read_text()
    offset = timedelta(milliseconds=int(offset_ms))
    items = list(srt.parse(raw))

    lines: List[SubtitleLine] = []
    for i, sub in enumerate(items, start=1):
        start = sub.start + offset
        end = sub.end + offset
        start_sec = max(0.0, start.total_seconds())
        end_sec = max(0.0, end.total_seconds())
        if end_sec <= start_sec:
            continue
        text = " ".join(sub.content.split())
        if not text:
            continue
        lines.append(SubtitleLine(index=i, start_sec=start_sec, end_sec=end_sec, text=text))
    return lines


def trim_srt(
    *,
    input_path: Path,
    output_path: Path,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    shift_to_zero: bool = True,
) -> Path:
    """
    Create a trimmed .srt limited to a time window.

    Args:
        input_path: Source .srt file path.
        output_path: Destination .srt file path.
        start_sec: Window start (seconds).
        end_sec: Window end (seconds). If None, runs to the end.
        shift_to_zero: If True, shift timestamps so window start becomes 0.

    Returns:
        Path to the trimmed .srt file.
    """
    start_td = _sec_to_timedelta(start_sec)
    end_td = _sec_to_timedelta(end_sec) if end_sec is not None else None

    items = list(srt.parse(input_path.read_text()))
    trimmed: List[srt.Subtitle] = []
    for idx, sub in enumerate(items, start=1):
        if end_td is not None and sub.start >= end_td:
            break
        if sub.end <= start_td:
            continue

        new_start = max(sub.start, start_td)
        new_end = sub.end if end_td is None else min(sub.end, end_td)
        if new_end <= new_start:
            continue

        if shift_to_zero:
            new_start -= start_td
            new_end -= start_td

        trimmed.append(
            srt.Subtitle(index=idx, start=new_start, end=new_end, content=sub.content)
        )

    for i, sub in enumerate(trimmed, start=1):
        sub.index = i

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(srt.compose(trimmed))
    return output_path


def align_dialogues_to_scenes(
    scenes: Iterable[Scene], subtitles: List[SubtitleLine]
) -> List[Dict[str, Any]]:
    """
    Attach subtitle lines to scenes based on time overlap.
    """
    aligned: List[Dict[str, Any]] = []
    for scene in scenes:
        dialogues = [
            {
                "start_sec": line.start_sec,
                "end_sec": line.end_sec,
                "text": line.text,
            }
            for line in subtitles
            if line.start_sec < scene.end_sec and line.end_sec > scene.start_sec
        ]
        aligned.append(
            {
                "scene_index": scene.scene_index,
                "start_sec": scene.start_sec,
                "end_sec": scene.end_sec,
                "duration_sec": scene.duration_sec,
                "dialogues": dialogues,
            }
        )
    return aligned


def run_timeline_base(
    *,
    artifacts_root: str | Path,
    series_id: str,
    episode_id: str,
    subtitle_path: Path,
    subtitle_offset_ms: int = 0,
) -> Path:
    """
    Build timeline_base.json by aligning subtitles to scenes.
    """
    dirs = episode_dirs(artifacts_root, episode_id, series_id)
    scenes = load_scene_list(dirs["scenes"])
    subtitles = parse_srt(subtitle_path, offset_ms=subtitle_offset_ms)

    payload = {
        "source": {
            "series_id": series_id,
            "episode_id": episode_id,
            "subtitle_path": str(subtitle_path),
            "subtitle_offset_ms": int(subtitle_offset_ms),
        },
        "scenes": align_dialogues_to_scenes(scenes, subtitles),
    }

    out_path = dirs["timeline"] / "timeline_base.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path
