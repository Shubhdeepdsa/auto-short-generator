from __future__ import annotations

import logging
from pathlib import Path
import typer

from autos.config import load_config
from autos.log import setup_logging
from autos.paths import episode_dirs, ensure_episode_dirs
from autos.run_meta import build_run_meta, write_run_meta

app = typer.Typer(help="Auto-Shorts Generator CLI (project bootstrap + pipeline stages).")  # Typer docs :contentReference[oaicite:10]{index=10}


@app.command()
def init(
    episode_id: str = typer.Option(..., "--episode-id", "-e", help="Unique episode id (folder name)."),
    config_path: Path = typer.Option(Path("config.yaml"), "--config", help="Path to config.yaml"),
):
    """
    Create the artifact folder structure + write run.json.
    """
    cfg = load_config(config_path)
    setup_logging(cfg.logging.get("level", "INFO"))
    log = logging.getLogger("autos")

    dirs = episode_dirs(cfg.artifacts_dir, episode_id)
    ensure_episode_dirs(dirs)

    run_meta = build_run_meta(cfg.model_dump())
    write_run_meta(dirs["root"] / "run.json", run_meta)

    log.info(f"✅ Initialized episode artifacts at: {dirs['root']}")


def main():
    app()
