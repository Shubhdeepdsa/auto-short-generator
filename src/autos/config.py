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
    subtitles: Dict[str, Any] = Field(
        default_factory=lambda: {"offset_ms": 0, "trim_start_sec": 0.0, "trim_end_sec": None}
    )
    frames: Dict[str, Any] = Field(
        default_factory=lambda: {
            "sample_points": [0.25, 0.5, 0.75],
            "min_scene_sec": 1.0,
            "format": "jpg",
            "quality": 2,
        }
    )
    vision: Dict[str, Any] = Field(
        default_factory=lambda: {
            "caption_model": "Salesforce/blip-image-captioning-base",
            "title_model": "",
            "device": "auto",
            "batch_size": 4,
            "title_max_words": 8,
            "title_temperature": 0.0,
        }
    )
    chunking: Dict[str, Any] = Field(
        default_factory=lambda: {"target_sec": 1800, "tolerance_sec": 120}
    )


class EnvOverrides(BaseSettings):
    """
    Environment variable overrides (12-factor style).
    Pydantic Settings is designed for env-driven config. :contentReference[oaicite:8]{index=8}
    """
    model_config = SettingsConfigDict(env_prefix="AUTOS_", extra="ignore")

    ARTIFACTS_DIR: Optional[str] = None
    LOG_LEVEL: Optional[str] = None
    CHUNK_TARGET_SEC: Optional[float] = None
    CHUNK_TOLERANCE_SEC: Optional[float] = None
    SUBTITLE_OFFSET_MS: Optional[int] = None
    SUBTITLE_TRIM_START_SEC: Optional[float] = None
    SUBTITLE_TRIM_END_SEC: Optional[float] = None
    FRAMES_SAMPLE_POINTS: Optional[str] = None
    FRAMES_MIN_SCENE_SEC: Optional[float] = None
    FRAMES_FORMAT: Optional[str] = None
    FRAMES_QUALITY: Optional[int] = None
    VISION_CAPTION_MODEL: Optional[str] = None
    VISION_TITLE_MODEL: Optional[str] = None
    VISION_DEVICE: Optional[str] = None
    VISION_BATCH_SIZE: Optional[int] = None
    VISION_TITLE_MAX_WORDS: Optional[int] = None
    VISION_TITLE_TEMPERATURE: Optional[float] = None


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
        value = value.strip()
        if value and value[0] in {'"', "'"}:
            value = value.strip().strip('"').strip("'")
        else:
            if " #" in value or "\t#" in value:
                value = value.split("#", 1)[0].rstrip()
            value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def _apply_dotenv(cfg: YamlConfig, data: Dict[str, str]) -> None:
    def _get_value(*keys: str) -> str | None:
        for key in keys:
            if key in data and data[key] != "":
                return data[key]
        return None

    artifacts_dir = _get_value("ARTIFACTS_DIR", "AUTOS_ARTIFACTS_DIR")
    if artifacts_dir is not None:
        cfg.artifacts_dir = artifacts_dir

    log_level = _get_value("LOG_LEVEL", "AUTOS_LOG_LEVEL")
    if log_level is not None:
        cfg.logging["level"] = log_level

    target_sec = _get_value("CHUNK_TARGET_SEC", "AUTOS_CHUNK_TARGET_SEC")
    if target_sec is not None:
        cfg.chunking["target_sec"] = float(target_sec)

    tolerance_sec = _get_value("CHUNK_TOLERANCE_SEC", "AUTOS_CHUNK_TOLERANCE_SEC")
    if tolerance_sec is not None:
        cfg.chunking["tolerance_sec"] = float(tolerance_sec)

    subtitle_offset = _get_value("SUBTITLE_OFFSET_MS", "AUTOS_SUBTITLE_OFFSET_MS")
    if subtitle_offset is not None:
        cfg.subtitles["offset_ms"] = int(float(subtitle_offset))

    subtitle_start = _get_value("SUBTITLE_TRIM_START_SEC", "AUTOS_SUBTITLE_TRIM_START_SEC")
    if subtitle_start is not None:
        cfg.subtitles["trim_start_sec"] = float(subtitle_start)

    subtitle_end = _get_value("SUBTITLE_TRIM_END_SEC", "AUTOS_SUBTITLE_TRIM_END_SEC")
    if subtitle_end is not None:
        cfg.subtitles["trim_end_sec"] = float(subtitle_end)

    frames_points = _get_value("FRAMES_SAMPLE_POINTS", "AUTOS_FRAMES_SAMPLE_POINTS")
    if frames_points is not None:
        cfg.frames["sample_points"] = [
            float(p.strip())
            for p in frames_points.split(",")
            if p.strip() != ""
        ]

    frames_min = _get_value("FRAMES_MIN_SCENE_SEC", "AUTOS_FRAMES_MIN_SCENE_SEC")
    if frames_min is not None:
        cfg.frames["min_scene_sec"] = float(frames_min)

    frames_fmt = _get_value("FRAMES_FORMAT", "AUTOS_FRAMES_FORMAT")
    if frames_fmt is not None:
        cfg.frames["format"] = frames_fmt

    frames_quality = _get_value("FRAMES_QUALITY", "AUTOS_FRAMES_QUALITY")
    if frames_quality is not None:
        cfg.frames["quality"] = int(float(frames_quality))

    vision_caption_model = _get_value("VISION_CAPTION_MODEL", "AUTOS_VISION_CAPTION_MODEL")
    if vision_caption_model is not None:
        cfg.vision["caption_model"] = vision_caption_model

    vision_title_model = _get_value("VISION_TITLE_MODEL", "AUTOS_VISION_TITLE_MODEL")
    if vision_title_model is not None:
        cfg.vision["title_model"] = vision_title_model

    vision_device = _get_value("VISION_DEVICE", "AUTOS_VISION_DEVICE")
    if vision_device is not None:
        cfg.vision["device"] = vision_device

    vision_batch = _get_value("VISION_BATCH_SIZE", "AUTOS_VISION_BATCH_SIZE")
    if vision_batch is not None:
        cfg.vision["batch_size"] = int(float(vision_batch))

    vision_max_words = _get_value("VISION_TITLE_MAX_WORDS", "AUTOS_VISION_TITLE_MAX_WORDS")
    if vision_max_words is not None:
        cfg.vision["title_max_words"] = int(float(vision_max_words))

    vision_temp = _get_value("VISION_TITLE_TEMPERATURE", "AUTOS_VISION_TITLE_TEMPERATURE")
    if vision_temp is not None:
        cfg.vision["title_temperature"] = float(vision_temp)


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

    if env.CHUNK_TARGET_SEC is not None:
        cfg.chunking["target_sec"] = float(env.CHUNK_TARGET_SEC)

    if env.CHUNK_TOLERANCE_SEC is not None:
        cfg.chunking["tolerance_sec"] = float(env.CHUNK_TOLERANCE_SEC)

    if env.SUBTITLE_OFFSET_MS is not None:
        cfg.subtitles["offset_ms"] = int(env.SUBTITLE_OFFSET_MS)

    if env.SUBTITLE_TRIM_START_SEC is not None:
        cfg.subtitles["trim_start_sec"] = float(env.SUBTITLE_TRIM_START_SEC)

    if env.SUBTITLE_TRIM_END_SEC is not None:
        cfg.subtitles["trim_end_sec"] = float(env.SUBTITLE_TRIM_END_SEC)

    if env.FRAMES_SAMPLE_POINTS is not None:
        cfg.frames["sample_points"] = [
            float(p.strip())
            for p in env.FRAMES_SAMPLE_POINTS.split(",")
            if p.strip() != ""
        ]

    if env.FRAMES_MIN_SCENE_SEC is not None:
        cfg.frames["min_scene_sec"] = float(env.FRAMES_MIN_SCENE_SEC)

    if env.FRAMES_FORMAT is not None:
        cfg.frames["format"] = env.FRAMES_FORMAT

    if env.FRAMES_QUALITY is not None:
        cfg.frames["quality"] = int(env.FRAMES_QUALITY)

    if env.VISION_CAPTION_MODEL is not None:
        cfg.vision["caption_model"] = env.VISION_CAPTION_MODEL

    if env.VISION_TITLE_MODEL is not None:
        cfg.vision["title_model"] = env.VISION_TITLE_MODEL

    if env.VISION_DEVICE is not None:
        cfg.vision["device"] = env.VISION_DEVICE

    if env.VISION_BATCH_SIZE is not None:
        cfg.vision["batch_size"] = int(env.VISION_BATCH_SIZE)

    if env.VISION_TITLE_MAX_WORDS is not None:
        cfg.vision["title_max_words"] = int(env.VISION_TITLE_MAX_WORDS)

    if env.VISION_TITLE_TEMPERATURE is not None:
        cfg.vision["title_temperature"] = float(env.VISION_TITLE_TEMPERATURE)

    return cfg
