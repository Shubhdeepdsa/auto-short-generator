from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autos.cli import app
from autos.config import load_dotenv

runner = CliRunner()
DOTENV = load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _write_config(path: Path, artifacts_dir: Path) -> None:
    path.write_text(
        "project_name: autos\n"
        f"artifacts_dir: {artifacts_dir}\n"
        "logging:\n"
        "  level: INFO\n"
    )
    dotenv_path = path.parent / ".env"
    dotenv_path.write_text(f"ARTIFACTS_DIR={artifacts_dir}\n")


def _require_video() -> Path:
    video = (
        os.environ.get("AUTOS_TEST_VIDEO")
        or os.environ.get("TEST_VIDEO")
        or DOTENV.get("AUTOS_TEST_VIDEO")
        or DOTENV.get("TEST_VIDEO")
    )
    if not video:
        pytest.skip("Set AUTOS_TEST_VIDEO to run scene-detect/thumbnail tests.")
    video_path = Path(video)
    if not video_path.exists():
        pytest.skip("AUTOS_TEST_VIDEO points to a missing file.")
    return video_path


def test_scene_merge_cli_writes_outputs(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    series_id = "seriesA"
    episode_id = "ep001"
    scenes_root = artifacts_dir / series_id / episode_id / "scenes"
    raw_dir = scenes_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    raw_scenes = [
        {"scene_index": 1, "start_sec": 0.0, "end_sec": 2.0, "duration_sec": 2.0},
        {"scene_index": 2, "start_sec": 2.0, "end_sec": 2.4, "duration_sec": 0.4},
        {"scene_index": 3, "start_sec": 2.4, "end_sec": 5.0, "duration_sec": 2.6},
        {"scene_index": 4, "start_sec": 5.0, "end_sec": 5.3, "duration_sec": 0.3},
        {"scene_index": 5, "start_sec": 5.3, "end_sec": 7.5, "duration_sec": 2.2},
    ]
    (raw_dir / "scenes.json").write_text(json.dumps(raw_scenes, indent=2))

    result = runner.invoke(
        app,
        [
            "scene-merge",
            "-s",
            series_id,
            "-e",
            episode_id,
            "--config",
            str(config_path),
            "--min-scene-sec",
            "1.0",
        ],
    )
    assert result.exit_code == 0, result.output

    merged_legacy = scenes_root / "merged_scenes.json"
    merged_legacy_csv = scenes_root / "merged_scenes.csv"
    merged_structured = scenes_root / "merged" / "scenes.json"
    merged_structured_csv = scenes_root / "merged" / "scenes.csv"
    assert merged_legacy.exists()
    assert merged_legacy_csv.exists()
    assert merged_structured.exists()
    assert merged_structured_csv.exists()

    merged = json.loads(merged_legacy.read_text())
    assert len(merged) <= len(raw_scenes)
    assert all(row["duration_sec"] >= 1.0 for row in merged)


def test_scene_detect_creates_raw_outputs(tmp_path: Path) -> None:
    video = _require_video()
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    result = runner.invoke(
        app,
        [
            "scene-detect",
            "-s",
            "seriesA",
            "-e",
            "ep001",
            "-v",
            str(video),
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output

    scenes_root = artifacts_dir / "seriesA" / "ep001" / "scenes"
    assert (scenes_root / "raw" / "scenes.json").exists()
    assert (scenes_root / "raw" / "scenes.csv").exists()


def test_scene_pipeline_exports_thumbs(tmp_path: Path) -> None:
    video = _require_video()
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    result = runner.invoke(
        app,
        [
            "scene-pipeline",
            "-s",
            "seriesA",
            "-e",
            "ep001",
            "-v",
            str(video),
            "--config",
            str(config_path),
            "--thumbs",
            "--merged-thumbs",
            "--thumbs-limit",
            "5",
        ],
    )
    assert result.exit_code == 0, result.output

    thumbs_raw = artifacts_dir / "seriesA" / "ep001" / "scenes" / "thumbs" / "raw"
    thumbs_merged = artifacts_dir / "seriesA" / "ep001" / "scenes" / "thumbs" / "merged"
    raw_images = list(thumbs_raw.glob("*.jpg"))
    merged_images = list(thumbs_merged.glob("*.jpg"))
    assert len(raw_images) >= 1
    assert len(merged_images) >= 1
