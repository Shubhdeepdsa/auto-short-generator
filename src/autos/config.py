from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class YamlConfig(BaseModel):
    project_name: str = "autos"
    artifacts_dir: str = "artifacts"

    logging: Dict[str, Any] = Field(default_factory=lambda: {"level": "INFO"})
    scene: Dict[str, Any] = Field(default_factory=dict)
    chunking: Dict[str, Any] = Field(default_factory=dict)


class EnvOverrides(BaseSettings):
    """
    Environment variable overrides (12-factor style).
    Pydantic Settings is designed for env-driven config. :contentReference[oaicite:8]{index=8}
    """
    model_config = SettingsConfigDict(env_prefix="AUTOS_", extra="ignore")

    ARTIFACTS_DIR: Optional[str] = None
    LOG_LEVEL: Optional[str] = None


def load_dotenv(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    data: Dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def _apply_dotenv(cfg: YamlConfig, data: Dict[str, str]) -> None:
    artifacts_dir = data.get("ARTIFACTS_DIR") or data.get("AUTOS_ARTIFACTS_DIR")
    if artifacts_dir:
        cfg.artifacts_dir = artifacts_dir

    log_level = data.get("LOG_LEVEL") or data.get("AUTOS_LOG_LEVEL")
    if log_level:
        cfg.logging["level"] = log_level


def load_config(config_path: str | Path = "config.yaml") -> YamlConfig:
    p = Path(config_path)
    if not p.exists():
        # No config file? Fine. Defaults still work.
        cfg = YamlConfig()
    else:
        raw = yaml.safe_load(p.read_text()) or {}
        cfg = YamlConfig.model_validate(raw)

    dotenv: Dict[str, str] = {}
    candidates = [Path(".env"), p.parent / ".env"]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        dotenv.update(load_dotenv(candidate))
    _apply_dotenv(cfg, dotenv)

    env = EnvOverrides()  # loads from environment variables :contentReference[oaicite:9]{index=9}

    if env.ARTIFACTS_DIR:
        cfg.artifacts_dir = env.ARTIFACTS_DIR

    if env.LOG_LEVEL:
        cfg.logging["level"] = env.LOG_LEVEL

    return cfg
