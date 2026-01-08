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


def load_config(config_path: str | Path = "config.yaml") -> YamlConfig:
    p = Path(config_path)
    if not p.exists():
        # No config file? Fine. Defaults still work.
        cfg = YamlConfig()
    else:
        raw = yaml.safe_load(p.read_text()) or {}
        cfg = YamlConfig.model_validate(raw)

    env = EnvOverrides()  # loads from environment variables :contentReference[oaicite:9]{index=9}

    if env.ARTIFACTS_DIR:
        cfg.artifacts_dir = env.ARTIFACTS_DIR

    if env.LOG_LEVEL:
        cfg.logging["level"] = env.LOG_LEVEL

    return cfg
