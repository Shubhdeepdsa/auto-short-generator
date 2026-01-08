from __future__ import annotations

import logging
from pathlib import Path
import typer

from autos.config import load_config
from autos.log import setup_logging
from autos.paths import episode_dirs, ensure_episode_dirs
from autos.run_meta import build_run_meta, write_run_meta
from autos.scene_detect import run_scene_detect
from autos.scene_merge import run_scene_merge
from autos.scene_thumbs import export_scene_thumbnails_from_json

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


@app.command("scene-merge")
def scene_merge(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    min_scene_sec: float = typer.Option(1.5, "--min-scene-sec", help="Minimum scene duration in seconds"),
    max_merge_chain: int = typer.Option(8, "--max-merge-chain", help="Max consecutive micro merges"),
    merged_thumbs: bool = typer.Option(False, "--merged-thumbs", help="Export thumbnails for merged scenes"),
    video: Path | None = typer.Option(None, "--video", "-v", help="Required when --merged-thumbs is set"),
    thumbs_limit: int = typer.Option(200, "--thumbs-limit", help="Max scenes to export thumbs for"),
    thumbs_num_images: int = typer.Option(1, "--thumbs-num-images", help="Images per scene"),
    thumbs_quality: int = typer.Option(90, "--thumbs-quality", help="JPG quality (encoder_param)"),
):
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    merged_json, merged_csv = run_scene_merge(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        min_scene_sec=min_scene_sec,
        max_merge_chain=max_merge_chain,
    )

    typer.echo("✅ Scene merge done.")
    typer.echo(f"Merged JSON → {merged_json}")
    typer.echo(f"Merged CSV → {merged_csv}")

    if merged_thumbs:
        if video is None:
            raise typer.BadParameter("--video is required when using --merged-thumbs.")
        dirs = episode_dirs(cfg.artifacts_dir, episode_id, series_id)
        merged_structured = dirs["scenes"] / "merged" / "scenes.json"
        export_scene_thumbnails_from_json(
            video=video,
            scenes_json=merged_structured,
            out_dir=dirs["scenes"] / "thumbs" / "merged",
            limit_scenes=thumbs_limit,
            num_images=thumbs_num_images,
            quality=thumbs_quality,
        )
        typer.echo(f"Merged thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/merged/")


@app.command("scene-pipeline")
def scene_pipeline(
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
    merged_thumbs: bool = typer.Option(False, "--merged-thumbs", help="Export thumbnails for merged scenes"),
    min_scene_sec: float = typer.Option(1.5, "--min-scene-sec", help="Minimum scene duration in seconds"),
    max_merge_chain: int = typer.Option(8, "--max-merge-chain", help="Max consecutive micro merges"),
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

    merged_json, merged_csv = run_scene_merge(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        min_scene_sec=min_scene_sec,
        max_merge_chain=max_merge_chain,
    )

    typer.echo("✅ Scene pipeline done.")
    typer.echo(f"Raw CSV → {csv_path}")
    typer.echo(f"Raw JSON → {json_path}")
    typer.echo(f"Merged JSON → {merged_json}")
    typer.echo(f"Merged CSV → {merged_csv}")
    if thumbs:
        typer.echo(f"Thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/raw/")
    if merged_thumbs:
        dirs = episode_dirs(cfg.artifacts_dir, episode_id, series_id)
        merged_structured = dirs["scenes"] / "merged" / "scenes.json"
        export_scene_thumbnails_from_json(
            video=video,
            scenes_json=merged_structured,
            out_dir=dirs["scenes"] / "thumbs" / "merged",
            limit_scenes=thumbs_limit,
            num_images=thumbs_num_images,
            quality=thumbs_quality,
        )
        typer.echo(f"Merged thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/merged/")


def main():
    app()
