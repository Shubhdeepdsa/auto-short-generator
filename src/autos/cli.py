from __future__ import annotations

import logging
from pathlib import Path
import typer

from autos.config import load_config
from autos.log import setup_logging
from autos.paths import episode_dirs, ensure_episode_dirs
from autos.run_meta import build_run_meta, write_run_meta
from autos.scene_detect import run_scene_detect

app = typer.Typer(help="Auto-Shorts Generator CLI (project bootstrap + pipeline stages).")


@app.callback()
def _cli() -> None:
    """Auto-Shorts Generator CLI (project bootstrap + pipeline stages)."""
    pass


@app.command()
def init(
    episode_id: str = typer.Option(..., "--episode-id", "-e", help="Unique episode id (folder name)."),
    series_id: str = typer.Option(..., "--series-id", "-s", help="Series id (artifacts/<series>/<episode>/...)"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
):
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
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    threshold: float = typer.Option(27.0, "--threshold", help="ContentDetector threshold"),
    progress: bool = typer.Option(False, "--progress", help="Show detection progress"),
    thumbs: bool = typer.Option(False, "--thumbs", help="Export scene thumbnails after detection"),
    thumbs_limit: int = typer.Option(200, "--thumbs-limit", help="Max scenes to export thumbs for"),
    thumbs_num_images: int = typer.Option(1, "--thumbs-num-images", help="Images per scene"),
    thumbs_quality: int = typer.Option(90, "--thumbs-quality", help="JPG quality (encoder_param)"),
):
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    csv_path, json_path = run_scene_detect(
        video=video,
        series_id=series_id,
        episode_id=episode_id,
        artifacts_root=cfg.artifacts_dir,
        threshold=threshold,
        show_progress=progress,
        export_thumbs=thumbs,
        thumbs_limit=thumbs_limit,
        thumbs_num_images=thumbs_num_images,
        thumbs_quality=thumbs_quality,
    )

    typer.echo("✅ Scene detection done.")
    typer.echo(f"CSV → {csv_path}")
    typer.echo(f"JSON → {json_path}")

    if thumbs:
        typer.echo(f"Thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/raw/")


def main():
    app()
