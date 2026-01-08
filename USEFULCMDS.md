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

This creates a clean artifact folder tree where all outputs for `ep001` will live.

### 3) Add raw video

Put your source video file(s) into:

```
artifacts/ep001/input/
```

---

## 📂 Resulting Folder Structure

When you run `auto init`, the following dirs are created:

```
artifacts/
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
uv run auto init --episode-id ep001
```

Creates artifact directories and writes run metadata.

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
uv run python -m autos.cli init --episode-id ep001
```

This always works even if `auto` isn’t registered.

---

## 🛠 Development Workflow

As you build more stages, these are example commands you’ll add:

```
uv run auto scene-detect --input path/to/video.mp4 --episode-id ep001
uv run auto chunk --episode-id ep001
uv run auto parse-subtitles --path subtitles.srt --episode-id ep001
uv run auto extract-frames --episode-id ep001
uv run auto apply-vision --episode-id ep001
uv run auto compute-scores --episode-id ep001
uv run auto plan-short --episode-id ep001 --target-length 180
uv run auto render --episode-id ep001
```

Each command:

* reads from `artifacts/<episode-id>/…`
* writes into another stage folder
* logs progress

---

## 🧪 Debugging & Verbose Logging

Sometimes you’ll want more detail:

```
AUTOS_LOG_LEVEL=DEBUG uv run auto scene-detect --episode-id ep001
```

This prints deeper internals so you can observe processing steps.

`AUTOS_LOG_LEVEL` supports:

* DEBUG
* INFO
* WARN
* ERROR

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
AUTOS_ARTIFACTS_DIR=custom_out uv run auto init --episode-id ep002
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
uv run auto init --episode-id ep001
```

Why?
This builds the workspace for an episode: every pipeline stage will write here, making results reproducible and organized.

---

### Step 3 — Add Input Files

```
artifacts/ep001/input/
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

### 1️⃣ Always add new output folders under `artifacts/<episode-id>/…`

Never write outside this tree.

### 2️⃣ Use descriptive episode IDs

Instead of `ep001`, use `episode_s1e02` so it’s human-friendly.

### 3️⃣ Don’t hardcode paths

Rely on configs and CLI options.

### 4️⃣ Log early and log often

Use `AUTOS_LOG_LEVEL=DEBUG` while developing each stage.

---

## ⚡ Quick Reference Table

| Task                        | Command                                         |
| --------------------------- | ----------------------------------------------- |
| Bootstrap project           | `uv init --app`                                 |
| Install deps + CLI          | `uv sync`                                       |
| Initialize episode          | `uv run auto init --episode-id ep001`           |
| View help                   | `uv run auto --help`                            |
| Run a stage directly        | `uv run python -m autos.cli <command>`          |
| Debug with verbose logs     | `AUTOS_LOG_LEVEL=DEBUG uv run auto <command>`   |
| Override artifacts location | `AUTOS_ARTIFACTS_DIR=path uv run auto init ...` |

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
