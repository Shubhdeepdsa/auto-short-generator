from __future__ import annotations

import json
from pathlib import Path

import srt
from typer.testing import CliRunner

from autos.cli import app
from autos.subtitles import trim_srt

runner = CliRunner()


def _write_config(path: Path, artifacts_dir: Path) -> None:
    path.write_text(
        "project_name: autos\n"
        f"artifacts_dir: {artifacts_dir}\n"
        "logging:\n"
        "  level: INFO\n"
        "subtitles:\n"
        "  offset_ms: 0\n"
        "  trim_start_sec: 0\n"
        "  trim_end_sec: 600\n"
    )
    dotenv_path = path.parent / ".env"
    dotenv_path.write_text(f"ARTIFACTS_DIR={artifacts_dir}\n")


def test_trim_srt_window(tmp_path: Path) -> None:
    input_path = tmp_path / "full.srt"
    output_path = tmp_path / "trimmed.srt"
    input_path.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n"
        "2\n00:00:05,000 --> 00:00:06,000\nWorld\n\n"
        "3\n00:00:09,000 --> 00:00:12,000\nEnd\n\n"
    )

    trim_srt(input_path=input_path, output_path=output_path, start_sec=0, end_sec=10)
    parsed = list(srt.parse(output_path.read_text()))

    assert len(parsed) == 3
    assert parsed[0].start.total_seconds() == 1.0
    assert parsed[2].end.total_seconds() == 10.0


def test_timeline_cli_aligns_dialogues(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    series_id = "seriesA"
    episode_id = "ep001"
    scenes_root = artifacts_dir / series_id / episode_id / "scenes" / "merged"
    scenes_root.mkdir(parents=True, exist_ok=True)
    merged_scenes = [
        {"scene_index": 1, "start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0},
        {"scene_index": 2, "start_sec": 5.0, "end_sec": 10.0, "duration_sec": 5.0},
    ]
    (scenes_root / "scenes.json").write_text(json.dumps(merged_scenes, indent=2))

    subtitle_path = artifacts_dir / series_id / episode_id / "input" / "episode.srt"
    subtitle_path.parent.mkdir(parents=True, exist_ok=True)
    subtitle_path.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n"
        "2\n00:00:06,000 --> 00:00:09,000\nWorld\n\n"
    )

    result = runner.invoke(
        app,
        [
            "timeline",
            "-s",
            series_id,
            "-e",
            episode_id,
            "--subtitle",
            str(subtitle_path),
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output

    timeline_path = artifacts_dir / series_id / episode_id / "timeline" / "timeline_base.json"
    payload = json.loads(timeline_path.read_text())

    scenes = payload["scenes"]
    assert len(scenes) == 2
    assert len(scenes[0]["dialogues"]) == 1
    assert scenes[0]["dialogues"][0]["text"] == "Hello"
    assert len(scenes[1]["dialogues"]) == 1
    assert scenes[1]["dialogues"][0]["text"] == "World"
