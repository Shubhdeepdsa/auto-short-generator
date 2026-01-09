# 🧠 Autos — Auto-Shorts Generator

A Python CLI pipeline that takes long videos and produces scene-aware short videos with transcripts, scoring, and deterministic structure.

This README is your **command reference and workflow guide** so you always know what to run, why it exists, and how it fits into the pipeline.

---

## 🚀 Quick Start

### 1) Bootstrap the project  
```bash
uv init --app
uv sync
````

This sets up a working Python environment, installs dependencies, and makes the CLI available.

### 2) Initialize an episode

```bash
uv run auto init -e ep001 -s seriesA
```

This creates a clean artifact folder tree where all outputs for `seriesA/ep001` will live.

### 3) Add raw video

Put your source video file(s) into:

```
artifacts/seriesA/ep001/input/
```

---

## 📂 Resulting Folder Structure

When you run `auto init`, the following dirs are created:

```
artifacts/
└── seriesA/
    └── ep001/
        ├── run.json         # metadata snapshot
        ├── input/           # raw inputs (video, subtitles)
        ├── scenes/          # scene detection outputs
        ├── chunks/          # grouped scenes
        ├── frames/          # sampled frames
        ├── vision/          # captions & titles
        ├── scores/          # scoring outputs
        ├── timeline/        # integrated scene+dialogue timeline
        ├── plans/           # LLM selection plans
        └── renders/         # final shorts & clips
```

This structure keeps each pipeline stage contained and traceable.

---

## 🧩 Common Commands

### 🛠 Environment & Package

#### `uv init --app`

Bootstraps the project. Generates config and sets up the development environment.

#### `uv sync`

Installs dependencies and your project package so `auto` commands work.

#### `uv lock`

Regenerates the lockfile for reproducible installs.

---

## 📟 Core CLI Commands

### 📌 Initialize Episode

```bash
uv run auto init --episode-id ep001 --series-id seriesA
```

Creates artifact directories and writes run metadata.

---

### 🎬 Scene Detect (raw scenes)

```bash
uv run auto scene-detect --video path/to/video.mp4 --series-id seriesA --episode-id ep001
```

Writes:
* `artifacts/<series-id>/<episode-id>/scenes/raw/scenes.json`
* `artifacts/<series-id>/<episode-id>/scenes/raw/scenes.csv`
* Legacy: `scenes/raw_scenes.json` + `scenes/raw_scenes.csv`

Add thumbnails:

```bash
uv run auto scene-detect --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --thumbs
```

---

### 🧱 Scene Merge (merged scenes)

```bash
uv run auto scene-merge --series-id seriesA --episode-id ep001
```

Writes:
* `artifacts/<series-id>/<episode-id>/scenes/merged/scenes.json`
* `artifacts/<series-id>/<episode-id>/scenes/merged/scenes.csv`
* Legacy: `scenes/merged_scenes.json` + `scenes/merged_scenes.csv`

Merged thumbnails (requires video path):

```bash
uv run auto scene-merge --series-id seriesA --episode-id ep001 --merged-thumbs --video path/to/video.mp4
```

---

### 🚀 Pipeline (detect + merge + chunk)

```bash
uv run auto pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --thumbs --merged-thumbs
```

Runs detect + merge + chunk in one call and writes raw/merged/chunks outputs (and thumbs if enabled).

Include subtitles to build timeline in the same run:

```bash
uv run auto pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --subtitle artifacts/seriesA/ep001/input/episode.srt
```

Optional offset:

```bash
uv run auto pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --subtitle artifacts/seriesA/ep001/input/episode.srt --subtitle-offset-ms 250
```

Only scene stages (no chunking):

```bash
uv run auto scene-pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --thumbs --merged-thumbs
```

---

### 📦 Chunk Scenes (nearest boundary rule)

```bash
uv run auto chunk --series-id seriesA --episode-id ep001
```

Override target/tolerance (seconds):

```bash
uv run auto chunk --series-id seriesA --episode-id ep001 --target-sec 600 --tolerance-sec 60
```

Writes:
* `artifacts/<series-id>/<episode-id>/chunks/chunks.json`

---

### 📝 Subtitles Trim (dev snippets)

Trim a full movie .srt down to a shorter window (e.g., first 10 minutes):

```bash
uv run auto subtitles-trim --input path/to/full.srt --output artifacts/seriesA/ep001_snip/input/episode_snip.srt --end-sec 600
```

If you set `SUBTITLE_TRIM_START_SEC` / `SUBTITLE_TRIM_END_SEC` in `.env`, you can omit the flags:

```bash
uv run auto subtitles-trim --input path/to/full.srt --output artifacts/seriesA/ep001_snip/input/episode_snip.srt
```

---

### 🧠 Timeline Build (align subtitles to scenes)

```bash
uv run auto timeline --series-id seriesA --episode-id ep001 --subtitle artifacts/seriesA/ep001/input/episode.srt
```

Optional offset:

```bash
uv run auto timeline --series-id seriesA --episode-id ep001 --subtitle artifacts/seriesA/ep001/input/episode.srt --subtitle-offset-ms 250
```

Writes:
* `artifacts/<series-id>/<episode-id>/timeline/timeline_base.json`

---

### 🧾 Chunk Summary (quick view)

```bash
uv run auto chunk-summary --series-id seriesA --episode-id ep001
```

Prints a one-line summary per chunk (scene range + timestamps).

---

## 🧪 Snippet Dev Commands (ep001_snip)

Use these while iterating on the snippet workflow:

```bash
ffmpeg -y -i og_test_files/Tenet.mp4 -ss 00:00:00 -t 600 -c copy snippets/ep001_snip.mp4
uv run auto init --episode-id ep001_snip --series-id seriesA
uv run auto pipeline --video snippets/ep001_snip.mp4 --series-id seriesA --episode-id ep001_snip --thumbs --merged-thumbs
uv run auto scene-merge --series-id seriesA --episode-id ep001_snip --merged-thumbs --video snippets/ep001_snip.mp4
uv run auto chunk --series-id seriesA --episode-id ep001_snip --target-sec 600 --tolerance-sec 60
uv run auto chunk-summary --series-id seriesA --episode-id ep001_snip
uv run auto subtitles-trim --input og_test_files/Tenet-English.srt --output artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt --end-sec 600
uv run auto timeline --series-id seriesA --episode-id ep001_snip --subtitle artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt
uv run auto pipeline --video snippets/ep001_snip.mp4 --series-id seriesA --episode-id ep001_snip --subtitle artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt
ls -la artifacts/seriesA/ep001_snip/scenes
find artifacts/seriesA/ep001_snip/scenes -maxdepth 5 -type f -iname "*merged*" -print
find artifacts/seriesA/ep001_snip/scenes -maxdepth 5 -type f \\( -iname "*.jpg" -o -iname "*.png" -o -iname "*.webp" \\) | head
```

If you set `TEST_VIDEO` in `.env`, you can run:

```bash
uv run auto scene-pipeline --video "$TEST_VIDEO" --series-id seriesA --episode-id ep001_snip --thumbs
```

---

### 🧠 Help & Info

```bash
uv run auto --help
```

Shows all top-level commands.

```bash
uv run auto <command> --help
```

Shows help for a specific command.

---

### 🧪 Direct Module Mode

If your CLI isn’t installed or you’re iterating code often, run:

```bash
uv run python -m autos.cli <command> [options]
```

Example:

```bash
uv run python -m autos.cli init --episode-id ep001 --series-id seriesA
```

This always works even if `auto` isn’t registered.

---

## 🛠 Development Workflow

As you build more stages, these are example commands you’ll add:

```
uv run auto scene-detect --video path/to/video.mp4 --series-id seriesA --episode-id ep001
uv run auto scene-merge --series-id seriesA --episode-id ep001
uv run auto scene-pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --thumbs
uv run auto chunk --series-id seriesA --episode-id ep001
uv run auto parse-subtitles --path subtitles.srt --series-id seriesA --episode-id ep001
uv run auto extract-frames --series-id seriesA --episode-id ep001
uv run auto apply-vision --series-id seriesA --episode-id ep001
uv run auto compute-scores --series-id seriesA --episode-id ep001
uv run auto plan-short --series-id seriesA --episode-id ep001 --target-length 180
uv run auto render --series-id seriesA --episode-id ep001
```

Each command:

* reads from `artifacts/<series-id>/<episode-id>/…`
* writes into another stage folder
* logs progress

---

## 🧪 Debugging & Verbose Logging

Sometimes you’ll want more detail:

```
AUTOS_LOG_LEVEL=DEBUG uv run auto scene-detect --series-id seriesA --episode-id ep001
```

This prints deeper internals so you can observe processing steps.

`AUTOS_LOG_LEVEL` supports:

* DEBUG
* INFO
* WARN
* ERROR

---

## 📄 .env File (no exporting needed)

Create a `.env` in repo root (copy from `.env.example`):

```bash
cp .env.example .env
```

Example `.env`:

```
ARTIFACTS_DIR=artifacts
LOG_LEVEL=INFO
TEST_VIDEO=snippets/ep001_snip.mp4
CHUNK_TARGET_SEC=600 # prod: 1800
CHUNK_TOLERANCE_SEC=60 # prod: 120
SUBTITLE_OFFSET_MS=0
SUBTITLE_TRIM_START_SEC=0
SUBTITLE_TRIM_END_SEC=600 # prod: unset
```

Notes:
* `ARTIFACTS_DIR` and `LOG_LEVEL` override `config.yaml`.
* `TEST_VIDEO` (or `AUTOS_TEST_VIDEO`) is used by tests automatically.
* You can also use `AUTOS_ARTIFACTS_DIR` / `AUTOS_LOG_LEVEL` in `.env` if you prefer.
* Chunking overrides: `CHUNK_TARGET_SEC`, `CHUNK_TOLERANCE_SEC` (or `AUTOS_`-prefixed).
* Subtitle overrides: `SUBTITLE_OFFSET_MS`, `SUBTITLE_TRIM_START_SEC`, `SUBTITLE_TRIM_END_SEC` (or `AUTOS_`-prefixed).

---

## ✅ Testing (Pytest)

Install dev dependencies:

```bash
uv sync --extra dev
```

Run all tests:

```bash
uv run pytest
```

Run scene-detect + thumbs tests (needs a real video file):

```bash
TEST_VIDEO=/path/to/video.mp4 uv run pytest
```

Why?
Scene-detect and thumbnail tests are skipped unless `TEST_VIDEO` or `AUTOS_TEST_VIDEO` points to a valid file.

---

## 🧠 Environment Overrides

You can override configuration without editing code.

| Env var               | Overrides                        |
| --------------------- | -------------------------------- |
| `AUTOS_ARTIFACTS_DIR` | changes the base artifact folder |
| `AUTOS_LOG_LEVEL`     | changes verbosity                |
| (future vars)         | scoring thresholds, model paths  |

Example:

```bash
AUTOS_ARTIFACTS_DIR=custom_out uv run auto init --episode-id ep002 --series-id seriesA
```

---

## 📋 Example Workflow With Explanations

Here’s a typical session:

### Step 1 — Bootstrap

```bash
uv init --app     # sets up project scaffolding
uv sync           # installs dependencies + CLI
```

Why?
Because `uv sync` creates a reproducible environment with libraries such as `typer`, `rich`, and other packages in `pyproject.toml`. It also installs your project package so the `auto` command is available.

---

### Step 2 — Initialize an Episode

```bash
uv run auto init --episode-id ep001 --series-id seriesA
```

Why?
This builds the workspace for an episode: every pipeline stage will write here, making results reproducible and organized.

---

### Step 3 — Add Input Files

```
artifacts/seriesA/ep001/input/
├── episode.mp4
└── episode.srt
```

Why?
Keeping input files inside the artifact tree ensures the pipeline has a single source of truth per run.

---

## 🧠 Why This Workflow Matters

This disciplined workflow gives you:

* **Reproducibility:** runs can be chased down by inspecting `run.json`.
* **Separation of stages:** results and artifacts don’t get mixed.
* **Debuggability:** logs + structure + predictable outputs.
* **Extendability:** new stages become new commands.

---

## 📌 Tips & Best Practices

### 1️⃣ Always add new output folders under `artifacts/<series-id>/<episode-id>/…`

Never write outside this tree.

### 2️⃣ Use descriptive episode IDs

Instead of `ep001`, use `episode_s1e02` so it’s human-friendly.

### 3️⃣ Don’t hardcode paths

Rely on configs and CLI options.

### 4️⃣ Log early and log often

Use `AUTOS_LOG_LEVEL=DEBUG` while developing each stage.

---

## ⚡ Quick Reference Table

| Task                        | Command                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| Bootstrap project           | `uv init --app`                                                                             |
| Install deps + CLI          | `uv sync`                                                                                   |
| Install dev deps (tests)    | `uv sync --extra dev`                                                                       |
| Initialize episode          | `uv run auto init --episode-id ep001 --series-id seriesA`                                   |
| Scene detect                | `uv run auto scene-detect --video path/to/video.mp4 --series-id seriesA --episode-id ep001` |
| Scene merge + thumbs        | `uv run auto scene-merge --series-id seriesA --episode-id ep001 --merged-thumbs --video path/to/video.mp4` |
| Pipeline (detect+merge+chunk) | `uv run auto pipeline --video path/to/video.mp4 --series-id seriesA --episode-id ep001 --thumbs --merged-thumbs` |
| Chunk scenes                | `uv run auto chunk --series-id seriesA --episode-id ep001`                                  |
| Chunk summary               | `uv run auto chunk-summary --series-id seriesA --episode-id ep001`                          |
| Subtitles trim              | `uv run auto subtitles-trim --input path/to/full.srt --output artifacts/seriesA/ep001/input/episode.srt --end-sec 600` |
| Timeline build              | `uv run auto timeline --series-id seriesA --episode-id ep001 --subtitle artifacts/seriesA/ep001/input/episode.srt` |
| Run tests                   | `TEST_VIDEO=path/to/video.mp4 uv run pytest`                                                 |
| View help                   | `uv run auto --help`                                                                        |
| Run a stage directly        | `uv run python -m autos.cli <command>`                                                      |
| Debug with verbose logs     | `AUTOS_LOG_LEVEL=DEBUG uv run auto <command>`                                               |
| Override artifacts location | `AUTOS_ARTIFACTS_DIR=path uv run auto init ... --series-id seriesA`                          |

---

## 🧠 Next Steps

After this foundation is solid, you’ll build:

1. 🚪 Scene detection
2. 📦 Scene merging & chunking
3. 🗣 Subtitle parsing
4. 🖼 Frame sampling
5. 🧠 Vision captioning
6. 📊 Scoring
7. 📜 Selection planning
8. ✂ Final rendering

Each stage will become a new CLI command that reads from and writes to the artifact tree.

---
