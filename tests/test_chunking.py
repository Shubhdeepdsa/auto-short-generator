from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from autos.chunker import Scene, build_chunks
from autos.cli import app

runner = CliRunner()


def _write_config(path: Path, artifacts_dir: Path) -> None:
    path.write_text(
        "project_name: autos\n"
        f"artifacts_dir: {artifacts_dir}\n"
        "logging:\n"
        "  level: INFO\n"
        "chunking:\n"
        "  target_sec: 600\n"
        "  tolerance_sec: 60\n"
    )
    dotenv_path = path.parent / ".env"
    dotenv_path.write_text(f"ARTIFACTS_DIR={artifacts_dir}\n")


def test_build_chunks_nearest_boundary() -> None:
    scenes = [
        Scene(scene_index=1, start_sec=0.0, end_sec=4.0),
        Scene(scene_index=2, start_sec=4.0, end_sec=9.0),
        Scene(scene_index=3, start_sec=9.0, end_sec=14.0),
        Scene(scene_index=4, start_sec=14.0, end_sec=19.0),
    ]
    chunks = build_chunks(scenes, target_sec=10.0, tolerance_sec=2.0)

    assert len(chunks) == 2
    assert chunks[0]["chunk_start_sec"] == 0.0
    assert chunks[0]["chunk_end_sec"] == 9.0
    assert chunks[1]["chunk_start_sec"] == 9.0
    assert chunks[1]["chunk_end_sec"] == 19.0


def test_chunk_cli_writes_output(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, artifacts_dir)

    series_id = "seriesA"
    episode_id = "ep001"
    scenes_root = artifacts_dir / series_id / episode_id / "scenes" / "merged"
    scenes_root.mkdir(parents=True, exist_ok=True)
    merged_scenes = [
        {"scene_index": 1, "start_sec": 0.0, "end_sec": 6.0, "duration_sec": 6.0},
        {"scene_index": 2, "start_sec": 6.0, "end_sec": 12.0, "duration_sec": 6.0},
        {"scene_index": 3, "start_sec": 12.0, "end_sec": 18.0, "duration_sec": 6.0},
    ]
    (scenes_root / "scenes.json").write_text(json.dumps(merged_scenes, indent=2))

    result = runner.invoke(
        app,
        [
            "chunk",
            "-s",
            series_id,
            "-e",
            episode_id,
            "--config",
            str(config_path),
        ],
    )
    assert result.exit_code == 0, result.output

    chunks_path = artifacts_dir / series_id / episode_id / "chunks" / "chunks.json"
    assert chunks_path.exists()
