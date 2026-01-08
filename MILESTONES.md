
## 0) Product “North Star” (so we don’t drift)

**Input:** a long video episode (e.g., 54 min) + optional subtitles (.srt/.vtt)
**Output:** a ~3 min short **made of whole scenes** (or subtitle-boundary trims only), with:

* a **scene timeline JSON** as the source of truth
* **debuggability**: you can inspect why each scene was chosen (scores + captions + dialogue)
* **hard constraints** enforced (no mid-scene / no mid-subtitle cuts)

If anything we build doesn’t move us toward that, it’s a side quest and we kill it.

---

## 1) How we’ll build (my opinionated workflow)

### Build order (because it de-risks the hardest unknowns early)

1. **Scene Detection** (global truth of structure)
2. **Scene Merge + Scene-aligned Chunking** (stability + scale)
3. **Subtitle parsing + alignment** (cheap signal, deterministic)
4. **Frame sampling** (enables vision)
5. **Vision caption → title** (scene semantics)
6. **Scoring** (cheap ranker, explainable)
7. **LLM selection under constraints** (story brain)
8. **FFmpeg cut + concat + subtitle burn** (final output)

This matches your README’s logic: structure first, intelligence later. 

---

## 2) Repo shape + artifact rules (so you don’t hate yourself later)

### Suggested repo structure

```
autos/
  cli.py
  config.py
  log.py

  scene_detect/
    engine.py         # interface
    scenedetect_impl.py
    ffmpeg_impl.py    # optional fallback
    merge.py

  chunking/
    chunker.py

  subtitles/
    parse_srt.py
    align.py

  frames/
    extract.py

  vision/
    caption.py
    title.py

  scoring/
    features.py
    score.py

  select/
    prompt.md
    selector.py
    constraints.py

  render/
    cut.py
    concat.py
    subtitles_ass.py
    burn_in.py
artifacts/
  <episode_id>/
    input/
    scenes/
    chunks/
    timeline/
    frames/
    vision/
    scores/
    plans/
    renders/
```

### Artifact contract (non-negotiable)

Every stage writes:

* `*.json` (machine truth)
* `*.csv` (human scan)
* optional `*.html` / preview images / short mp4 snippets

This is how you stay sane while iterating.

---

## 3) Milestones + Stories (your task doc)

### Milestone M0 — Project bootstrap (1-time foundation)

**Goal:** you can run `autos ...` commands and produce artifacts in a consistent folder layout.

**STORY M0-1: CLI skeleton + config**

* **Deliverable:** `autos run scene-detect --input <path> --episode-id <id>`
* **Acceptance:**

  * CLI runs on your machine
  * creates `artifacts/<episode_id>/...` directories
  * writes `run.json` containing config + git commit hash (if available) + timestamps
* **Notes:** use a single `config.yaml` or `config.json` so thresholds aren’t hardcoded.

**STORY M0-2: Logging + error discipline**

* **Acceptance:**

  * every stage logs start/end + key counts (scene count, chunk count)
  * failures produce a readable error + preserve partial artifacts

---

### Milestone M1 — Scene detection (your “start building now” milestone)

**Goal:** given a long video, output a clean list of scene boundaries + debug exports.

#### Why PySceneDetect first (practical + proven)

PySceneDetect can detect cuts and export scene lists cleanly via CLI/API. The CLI supports `detect-content` and `list-scenes` which writes a scene table to CSV. ([SceneDetect][1])

**STORY M1-1: Scene detection adapter (PySceneDetect)**

* **Deliverables:**

  * `artifacts/<id>/scenes/raw_scenes.csv`
  * `artifacts/<id>/scenes/raw_scenes.json`
* **Acceptance:**

  * Scene list contains: `scene_index, start_sec, end_sec, duration_sec`
  * Runs on a full 54-min episode without crashing
* **Implementation hint (CLI):**

  * Use PySceneDetect CLI to generate CSV: `list-scenes` outputs scene boundaries. ([SceneDetect][2])

**STORY M1-2: Optional sanity-check engine (FFmpeg scene filter)**
This is not the main path, it’s a **debug cross-check**.

* FFmpeg can output frames where `scene` score crosses a threshold using `select='gt(scene,0.4)'` with `showinfo`. ([Stack Overflow][3])
* **Acceptance:**

  * you can run a command and see candidate cut timestamps in logs
  * you can compare cut density vs PySceneDetect (spot glaring issues)

**STORY M1-3: Micro-scene merge pass**
Scene detection often produces tiny “flash” scenes. Your README already calls out a merge pass for micro-scenes. 

* **Rules (configurable):**

  * `MIN_SCENE_SEC` (e.g. 1.0–2.0s): merge into neighbor
  * `MAX_MERGE_CHAIN`: prevent merging half the episode accidentally
* **Acceptance:**

  * Output `merged_scenes.json`
  * No scene shorter than `MIN_SCENE_SEC` unless it’s unavoidable (edge cases)

**STORY M1-4: Scene preview exporter**

* **Deliverable options:**

  * for each scene, save 1 thumbnail at midpoint **or** a contact sheet
* **Acceptance:**

  * you can visually audit if scene boundaries look real

---

### Milestone M2 — Scene-aligned chunking (scale without breaking structure)

Your chunking rule: “target ~30min, never cut mid-scene, choose nearest boundary with tolerance.” 

**STORY M2-1: Chunk builder (Nearest Scene Boundary Rule)**

* **Inputs:** `merged_scenes.json`
* **Outputs:**

  * `chunks.json` containing chunk ranges (by scene indices + timestamps)
* **Acceptance:**

  * No chunk boundary splits a scene
  * Chunk duration is close to target (e.g. 1800s) within tolerance where possible
  * Deterministic output (same input → same chunks)

---

### Milestone M3 — Subtitles parsing + dialogue alignment (cheap high-signal)

**Goal:** map subtitle lines into scenes deterministically.

You can use Python libs like `srt` to parse SRT reliably. ([PyPI][4])
(You can also use `pysrt`, but `srt` is clean and tiny.) ([GitHub][5])

**STORY M3-1: Subtitle parser**

* **Acceptance:**

  * reads `.srt` into a list of `{start_ms, end_ms, text}`
  * supports `subtitle_offset_ms` (positive/negative) for drift correction (per your README) 

**STORY M3-2: Align dialogues to scenes**

* **Acceptance:**

  * each scene gets `dialogues[]` containing only subtitle lines whose timestamps overlap scene window
  * output: `timeline_base.json` (scenes + dialogues, no vision yet)

---

### Milestone M4 — Frame sampling per scene

Your README explicitly prefers **multi-frame sampling** (25%, 50%, 75%). 

**STORY M4-1: Frame extractor**

* **Acceptance:**

  * for each scene, extract 3 frames into `frames/<scene_id>/`
  * handles very short scenes (fallback to 1 frame)
* **Implementation:** use FFmpeg to seek and extract frames (fast + deterministic).

---

### Milestone M5 — Vision caption → title

Pick a local vision caption approach:

* **BLIP** supports image captioning (good baseline). ([GitHub][6])
* **LLaVA** is a stronger multimodal assistant (heavier). ([LLaVA][7])

**STORY M5-1: Caption frames**

* **Acceptance:**

  * each scene produces `visual_caption` (string)
  * store raw captions for each of 3 frames + merged caption

**STORY M5-2: Title generator**

* **Acceptance:**

  * `title` is short and punchy (<= 8 words)
  * deterministic mode available (temperature=0) so debug runs don’t reshuffle reality

---

### Milestone M6 — Scoring layer (the “boring-but-wins” component)

Your README’s core point: scoring reduces chaos and filters candidates before the LLM. 

**STORY M6-1: Feature computation**

* dialogue density (words/sec)
* dialogue presence ratio
* keyword intensity
* visual salience heuristics (action verbs, people count approximations from caption)
* length penalty

**STORY M6-2: Total score + ranking**

* **Acceptance:**

  * produce `scores.csv` sorted by `total_score`
  * expose weights in config
  * log top 10 scenes with feature breakdown

---

### Milestone M7 — LLM selection under hard constraints

**Goal:** LLM picks “what scenes”, system enforces “how it can cut”. 

**STORY M7-1: Candidate packer**

* Input: top-K scenes (e.g. 30–60)
* Output: compact JSON passed to LLM (token-safe)

**STORY M7-2: Constraint enforcer**
Hard rules:

* never cut mid-scene
* never start/end mid-subtitle
* trim only at subtitle boundaries
  (all straight from your README) 

**STORY M7-3: Selection plan output**

* Output: `plan.json` with ordered scene list + target duration window

---

### Milestone M8 — Render: cut + concat + subtitle burn-in

FFmpeg concat demuxer is the recommended practical method. ([FFmpeg Trac][8])
Burn subtitles using FFmpeg `subtitles`/`ass` filters (libass). ([FFmpeg Trac][9])

**STORY M8-1: Scene cutter**

* **Acceptance:** each selected scene becomes a clip file with exact timestamps

**STORY M8-2: Concatenation**

* **Acceptance:** clips are joined in order using concat demuxer ([FFmpeg Trac][8])

**STORY M8-3: Subtitle styling + burn**

* **Acceptance:** consistent subtitle style across output
* **Reference:** FFmpeg wiki shows burning with `subtitles` or `ass`. ([FFmpeg Trac][9])

---

## 4) “Questions to calibrate your competence” (so I assign the right tasks)

Answer these once, and I’ll tune the backlog (tools, difficulty, and how much I spoon-feed vs assume).

### A) Environment & video reality

1. OS + hardware: Mac (M-series?) or Linux/Windows? GPU available?
2. Typical input format: mp4/h264? variable framerate? 1080p/4K?
3. Do you already have subtitles for episodes, or do we need STT later?

### B) Comfort level (honest answers help)

4. FFmpeg level: beginner / okay / strong?
5. Python level: beginner / okay / strong?
6. Do you want a CLI-only first, or a tiny web UI for browsing scenes early?

### C) Quality target

7. Are we optimizing for **throughput** (many episodes) or **quality per episode**?
8. Shorts format: 9:16 crop + captions mandatory, or just clipping first?

### D) Local model constraints

9. Are you okay downloading multi-GB models locally for captioning/LLM?
10. Do you prefer “fast and decent” (BLIP + small LLM) or “heavier but smarter” (LLaVA-class VLM)?

---

## 5) Your immediate “Start Now” task list (next 2 moves)

If you want the cleanest, fastest start that produces real progress:

### ✅ Do next:

1. **M0-1 (CLI + artifacts folder)**
2. **M1-1 (PySceneDetect scene export) + M1-3 (micro-scene merge)**

That gets you the first *real* core artifact: `merged_scenes.json`. Everything else builds on that.

---

When you complete **M1**, you’ll already have something satisfying: *a 54-minute episode turned into a clean structured scene list you can inspect and trust*. After that, the rest is just stacking Lego bricks with increasing intelligence.

[1]: https://www.scenedetect.com/docs/latest/cli.html?utm_source=chatgpt.com "scenedetect Command — PySceneDetect 0.6.6 documentation"
[2]: https://www.scenedetect.com/docs/0.6.1/cli/commands.html?utm_source=chatgpt.com "Commands — PySceneDetect v0.6.1 documentation"
[3]: https://stackoverflow.com/questions/35675529/using-ffmpeg-how-to-do-a-scene-change-detection-with-timecode?utm_source=chatgpt.com "Using FFMPEG: How to do a Scene Change Detection? with ..."
[4]: https://pypi.org/project/srt/?utm_source=chatgpt.com "srt - PyPI"
[5]: https://github.com/byroot/pysrt?utm_source=chatgpt.com "byroot/pysrt: Python parser for SubRip (srt) files - GitHub"
[6]: https://github.com/salesforce/BLIP?utm_source=chatgpt.com "PyTorch code for BLIP: Bootstrapping Language-Image Pre-training ..."
[7]: https://llava-vl.github.io/?utm_source=chatgpt.com "LLaVA"
[8]: https://trac.ffmpeg.org/wiki/Concatenate?utm_source=chatgpt.com "Concatenate - FFmpeg Wiki"
[9]: https://trac.ffmpeg.org/wiki/HowToBurnSubtitlesIntoVideo?utm_source=chatgpt.com "HowToBurnSubtitlesIntoVideo - FFmpeg Wiki"
