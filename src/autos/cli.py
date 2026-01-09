from __future__ import annotations

import logging
from pathlib import Path
import typer

from autos.config import load_config
from autos.log import setup_logging
from autos.paths import episode_dirs, ensure_episode_dirs
from autos.run_meta import build_run_meta, write_run_meta
from autos.chunker import format_chunk_summary, load_chunks, run_chunking
from autos.frames import format_frames_summary, run_frame_extraction
from autos.scene_detect import run_scene_detect
from autos.scene_merge import run_scene_merge
from autos.scene_thumbs import export_scene_thumbnails_from_json
from autos.subtitles import run_timeline_base, trim_srt

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


@app.command("pipeline")
def pipeline(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    video: Path = typer.Option(..., "--video", "-v", help="Path to input video"),
    subtitle_path: Path | None = typer.Option(None, "--subtitle", help="Optional .srt for timeline"),
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
    target_sec: float | None = typer.Option(None, "--target-sec", help="Target chunk duration in seconds"),
    tolerance_sec: float | None = typer.Option(None, "--tolerance-sec", help="Allowed deviation in seconds"),
    subtitle_offset_ms: int | None = typer.Option(
        None, "--subtitle-offset-ms", help="Subtitle timing offset (ms)"
    ),
    frames: bool = typer.Option(True, "--frames/--no-frames", help="Extract frames per scene"),
    frames_sample_points: str | None = typer.Option(
        None, "--frames-sample-points", help="Comma-separated sample points (e.g. 0.25,0.5,0.75)"
    ),
    frames_min_scene_sec: float | None = typer.Option(
        None, "--frames-min-scene-sec", help="Min scene duration for multi-sampling"
    ),
    frames_format: str | None = typer.Option(None, "--frames-format", help="Image format (jpg|png)"),
    frames_quality: int | None = typer.Option(None, "--frames-quality", help="jpg:2-31, png:0-9"),
):
    """
    Run scene detection + merge + chunking in a single command.
    """
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

    target = (
        target_sec
        if target_sec is not None
        else float(cfg.chunking.get("target_sec", 1800))
    )
    tolerance = (
        tolerance_sec
        if tolerance_sec is not None
        else float(cfg.chunking.get("tolerance_sec", 120))
    )

    chunks_path = run_chunking(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        target_sec=target,
        tolerance_sec=tolerance,
    )

    frames_root: Path | None = None
    if frames:
        sample_points = (
            [float(p.strip()) for p in frames_sample_points.split(",") if p.strip() != ""]
            if frames_sample_points is not None
            else cfg.frames.get("sample_points", [0.25, 0.5, 0.75])
        )
        min_scene = (
            frames_min_scene_sec
            if frames_min_scene_sec is not None
            else float(cfg.frames.get("min_scene_sec", 1.0))
        )
        fmt = frames_format if frames_format is not None else cfg.frames.get("format", "jpg")
        quality = (
            frames_quality
            if frames_quality is not None
            else int(cfg.frames.get("quality", 2))
        )
        frames_root = run_frame_extraction(
            artifacts_root=cfg.artifacts_dir,
            series_id=series_id,
            episode_id=episode_id,
            video=video,
            sample_points=sample_points,
            min_scene_sec=min_scene,
            image_format=str(fmt),
            quality=int(quality),
        )

    timeline_path: Path | None = None
    if subtitle_path is not None:
        offset = (
            subtitle_offset_ms
            if subtitle_offset_ms is not None
            else int(cfg.subtitles.get("offset_ms", 0))
        )
        timeline_path = run_timeline_base(
            artifacts_root=cfg.artifacts_dir,
            series_id=series_id,
            episode_id=episode_id,
            subtitle_path=subtitle_path,
            subtitle_offset_ms=offset,
        )

    typer.echo("✅ Pipeline done.")
    typer.echo(f"Raw CSV → {csv_path}")
    typer.echo(f"Raw JSON → {json_path}")
    typer.echo(f"Merged JSON → {merged_json}")
    typer.echo(f"Merged CSV → {merged_csv}")
    typer.echo(f"Chunks → {chunks_path}")
    if frames_root is not None:
        typer.echo(f"Frames → {frames_root}")
    if timeline_path is not None:
        typer.echo(f"Timeline → {timeline_path}")
    if thumbs:
        typer.echo(f"Thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/raw/")
    if merged_thumbs:
        typer.echo(f"Merged thumbs → artifacts/{series_id}/{episode_id}/scenes/thumbs/merged/")


@app.command("chunk")
def chunk(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    target_sec: float | None = typer.Option(None, "--target-sec", help="Target chunk duration in seconds"),
    tolerance_sec: float | None = typer.Option(None, "--tolerance-sec", help="Allowed deviation in seconds"),
):
    """
    Build scene-aligned chunks using merged scenes and the nearest-boundary rule.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    target = (
        target_sec
        if target_sec is not None
        else float(cfg.chunking.get("target_sec", 1800))
    )
    tolerance = (
        tolerance_sec
        if tolerance_sec is not None
        else float(cfg.chunking.get("tolerance_sec", 120))
    )

    out_path = run_chunking(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        target_sec=target,
        tolerance_sec=tolerance,
    )

    typer.echo("✅ Chunking done.")
    typer.echo(f"Chunks → {out_path}")


@app.command("chunk-summary")
def chunk_summary(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
):
    """
    Print a one-line summary for each chunk in chunks/chunks.json.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    chunks_path = episode_dirs(cfg.artifacts_dir, episode_id, series_id)["chunks"] / "chunks.json"
    chunks = load_chunks(chunks_path)
    typer.echo(f"Chunks → {chunks_path}")
    for line in format_chunk_summary(chunks):
        typer.echo(line)


@app.command("extract-frames")
def extract_frames(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    video: Path = typer.Option(..., "--video", "-v", help="Path to input video"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    sample_points: str | None = typer.Option(
        None, "--sample-points", help="Comma-separated sample points (e.g. 0.25,0.5,0.75)"
    ),
    min_scene_sec: float | None = typer.Option(
        None, "--min-scene-sec", help="Min scene duration for multi-sampling"
    ),
    image_format: str | None = typer.Option(None, "--format", help="Image format (jpg|png)"),
    quality: int | None = typer.Option(None, "--quality", help="jpg:2-31, png:0-9"),
):
    """
    Extract sample frames per scene into artifacts/<series>/<episode>/frames/.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    points = (
        [float(p.strip()) for p in sample_points.split(",") if p.strip() != ""]
        if sample_points is not None
        else cfg.frames.get("sample_points", [0.25, 0.5, 0.75])
    )
    min_scene = min_scene_sec if min_scene_sec is not None else float(cfg.frames.get("min_scene_sec", 1.0))
    fmt = image_format if image_format is not None else cfg.frames.get("format", "jpg")
    q = quality if quality is not None else int(cfg.frames.get("quality", 2))

    frames_root = run_frame_extraction(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        video=video,
        sample_points=points,
        min_scene_sec=min_scene,
        image_format=str(fmt),
        quality=int(q),
    )

    typer.echo("✅ Frame extraction done.")
    typer.echo(f"Frames → {frames_root}")


@app.command("frames-summary")
def frames_summary(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
):
    """
    Print a summary of extracted frames per scene.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    frames_root = episode_dirs(cfg.artifacts_dir, episode_id, series_id)["frames"]
    typer.echo(f"Frames → {frames_root}")
    for line in format_frames_summary(frames_root):
        typer.echo(line)


@app.command("subtitles-trim")
def subtitles_trim(
    input_path: Path = typer.Option(..., "--input", "-i", help="Path to full .srt file"),
    output_path: Path = typer.Option(..., "--output", "-o", help="Path to trimmed .srt file"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    start_sec: float | None = typer.Option(None, "--start-sec", help="Trim window start (seconds)"),
    end_sec: float | None = typer.Option(None, "--end-sec", help="Trim window end (seconds)"),
    shift_to_zero: bool = typer.Option(True, "--shift-to-zero/--no-shift-to-zero"),
):
    """
    Trim a full subtitles file into a shorter dev snippet.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    start = (
        start_sec
        if start_sec is not None
        else float(cfg.subtitles.get("trim_start_sec", 0.0))
    )
    end = end_sec if end_sec is not None else cfg.subtitles.get("trim_end_sec")
    end_val = float(end) if end is not None else None

    out_path = trim_srt(
        input_path=input_path,
        output_path=output_path,
        start_sec=start,
        end_sec=end_val,
        shift_to_zero=shift_to_zero,
    )
    typer.echo("✅ Subtitles trimmed.")
    typer.echo(f"SRT → {out_path}")


@app.command("timeline")
def timeline(
    series_id: str = typer.Option(..., "--series-id", "-s"),
    episode_id: str = typer.Option(..., "--episode-id", "-e"),
    subtitle_path: Path = typer.Option(..., "--subtitle", help="Path to .srt file"),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
    subtitle_offset_ms: int | None = typer.Option(
        None, "--subtitle-offset-ms", help="Subtitle timing offset (ms)"
    ),
):
    """
    Build timeline_base.json by aligning subtitles to scenes.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))

    offset = (
        subtitle_offset_ms
        if subtitle_offset_ms is not None
        else int(cfg.subtitles.get("offset_ms", 0))
    )

    out_path = run_timeline_base(
        artifacts_root=cfg.artifacts_dir,
        series_id=series_id,
        episode_id=episode_id,
        subtitle_path=subtitle_path,
        subtitle_offset_ms=offset,
    )
    typer.echo("✅ Timeline built.")
    typer.echo(f"Timeline → {out_path}")


def main():
    app()
