from pathlib import Path
from typing import Dict

def episode_dirs(artifacts_root: str | Path, episode_id: str) -> Dict[str, Path]:
    root = Path(artifacts_root) / episode_id
    return {
        "root": root,
        "input": root / "input",
        "scenes": root / "scenes",
        "chunks": root / "chunks",
        "timeline": root / "timeline",
        "frames": root / "frames",
        "vision": root / "vision",
        "scores": root / "scores",
        "plans": root / "plans",
        "renders": root / "renders",
    }

def ensure_episode_dirs(dirs: Dict[str, Path]) -> None:
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
