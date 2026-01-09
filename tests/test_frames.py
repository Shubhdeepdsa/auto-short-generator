from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autos.cli import app
from autos.frames import compute_sample_points, format_frames_summary
from autos.chunker import Scene

runner = CliRunner()


def _write_config(path: Path, artifacts_dir: Path) -> None:
    path.write_text(
        "project_name: autos\n"
        f"artifacts_dir: {artifacts_dir}\n"
        "logging:\n"
        "  level: INFO\n"
        "frames:\n"
        "  sample_points: [0.25, 0.5, 0.75]\n"
        "  min_scene_sec: 1.0\n"
        "  format: jpg\n"
        "  quality: 2\n"
    )
    dotenv_path = path.parent / ".env"
    dotenv_path.write_text(f"ARTIFACTS_DIR={artifacts_dir}\n")


def _require_video() -> Path:
    video = os.environ.get("TEST_VIDEO") or os.environ.get("AUTOS_TEST_VIDEO")
    if not video:
        pytest.skip("Set TEST_VIDEO or AUTOS_TEST_VIDEO to run frame extraction tests.")
    video_path = Path(video)
    if not video_path.exists():
        pytest.skip("TEST_VIDEO points to a missing file.")
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not available on PATH.")
    return video_path


def test_compute_sample_points_midpoint_for_short_scene() -> None:
    scene = Scene(scene_index=1, start_sec=0.0, end_sec=0.5)
    samples = compute_sample_points(scene, sample_points=[0.25, 0.5, 0.75], min_scene_sec=1.0)
    assert len(samples) == 1
    assert samples[0].label == "50"


def test_extract_frames_cli(tmp_path: Path) -> None:
    video = _require_video()
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    series_id = "seriesA"
    episode_id = "ep001"
    scenes_root = artifacts_dir / series_id / episode_id / "scenes" / "merged"
    scenes_root.mkdir(parents=True, exist_ok=True)
    merged_scenes = [
        {"scene_index": 1, "start_sec": 0.0, "end_sec": 2.0, "duration_sec": 2.0},
        {"scene_index": 2, "start_sec": 2.0, "end_sec": 4.0, "duration_sec": 2.0},
    ]
    (scenes_root / "scenes.json").write_text(json.dumps(merged_scenes, indent=2))

    result = runner.invoke(
        app,
        [
            "extract-frames",
            "-s",
            series_id,
            "-e",
            episode_id,
            "-v",
            str(video),
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output

    frames_root = artifacts_dir / series_id / episode_id / "frames"
    assert frames_root.exists()
    assert any(frames_root.rglob("*.jpg"))


def test_frames_summary(tmp_path: Path) -> None:
    frames_root = tmp_path / "frames"
    (frames_root / "scene_0001").mkdir(parents=True, exist_ok=True)
    (frames_root / "scene_0002").mkdir(parents=True, exist_ok=True)
    (frames_root / "scene_0001" / "frame_25.jpg").write_text("x")
    (frames_root / "scene_0001" / "frame_50.jpg").write_text("x")
    (frames_root / "scene_0002" / "frame_50.jpg").write_text("x")

    lines = format_frames_summary(frames_root)
    assert "scene_0001: 2 frames" in lines
    assert "scene_0002: 1 frames" in lines
    assert lines[-1] == "total: 3 frames"
