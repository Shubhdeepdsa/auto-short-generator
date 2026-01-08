from __future__ import annotations

import logging
from pathlib import Path
import typer

from autos.config import load_config
from autos.log import setup_logging
from autos.paths import episode_dirs, ensure_episode_dirs
from autos.run_meta import build_run_meta, write_run_meta
from autos.scene_detect import run_scene_detect

app = typer.Typer(help="Auto-Shorts Generator CLI (project bootstrap + pipeline stages).")  # Typer docs :contentReference[oaicite:10]{index=10}


@app.callback()
def _cli() -> None:
    """Auto-Shorts Generator CLI (project bootstrap + pipeline stages)."""
    pass


@app.command()
def init(
    episode_id: str = typer.Option(..., "--episode-id", "-e", help="Unique episode id (folder name)."),
    series_id: str = typer.Option(
        ...,
        "--series-id",
        "-s",
        help="Series id (creates artifacts/<series>/<episode>/...).",
    ),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
):
    """
    Create the artifact folder structure + write run.json.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))
    log = logging.getLogger("autos")

    dirs = episode_dirs(cfg.artifacts_dir, episode_id, series_id)
    ensure_episode_dirs(dirs)

    run_meta = build_run_meta(cfg.model_dump())
    write_run_meta(dirs["root"] / "run.json", run_meta)

    log.info(f"✅ Initialized episode artifacts at: {dirs['root']}")

@app.command("scene-detect")
def scene_detect(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    video: Path = typer.Option(..., "--video", "-v", help="Path to input video"),
):
    """
    Detect scenes in the given video and write outputs under
    artifacts/<series_id>/<episode_id>/scenes/
    """
    run_scene_detect(video, series_id, episode_id)

def main():
    app()
