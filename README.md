# 🎬 AutoShorts
**A local-first, structured pipeline for turning long-form video into coherent, high-quality Shorts — with explainable scoring and hard constraints.**

---

## What is AutoShorts?

**AutoShorts** is an open-source project that explores a simple, practical idea:

> If we respect the natural structure of video (scenes + dialogue + visuals), we can generate coherent short-form clips locally — without cloud APIs, paid tools, or heavy infrastructure.

Most “AI video” projects either:
- throw raw video into a black box (expensive + slow), or
- slice transcripts blindly (cheap but incoherent).

AutoShorts is the third path:
- **extract structure first**, then
- **use local models to make decisions**, then
- **assemble clips deterministically**.

The result is a pipeline that can process **full episodes or movies** and generate **~3-minute clips** suitable for platforms like YouTube Shorts — while staying **local**, **inspectable**, and **fast enough** to run on a laptop (e.g. Apple M-series).

---

## Why this exists (the real motivation)

Short-form content is everywhere, but automation usually fails in predictable ways:

- Transcript-only systems lose *visual context* and pick “meh” scenes.
- Video-only systems are compute-hungry and hard to debug.
- LLM-only “pick interesting parts” systems produce random clip salad.

AutoShorts was built around a simple belief:

> Structure makes intelligence cheap.

If we turn the episode into a structured timeline of scenes + dialogue + visual descriptions, then even smaller local models can make good selections — and every decision becomes auditable.

---

## Design principles

### 1) Local-first by default
No cloud requirements. The pipeline is designed to work with:
- FFmpeg
- open-source Python tools
- local text LLMs
- local vision captioning / VLM models

### 2) Structure before intelligence
We don’t start with “AI decides everything.”
We start with **scene boundaries**, **dialogue timing**, and **visual context**.

### 3) Explainable intermediate artifacts
The core output is a **scene-level JSON timeline**.
You can inspect it, rerun selection, re-rank scenes, and iterate without reprocessing the full video.

### 4) Hard constraints prevent garbage outputs
The LLM isn’t allowed to cut arbitrarily.
The system enforces rules like:
- never cut mid-scene
- never cut mid-subtitle
- target duration ~3 minutes

### 5) Performance over perfection
The goal is **repeatable quality at scale on local hardware**, not a one-off demo.

---

## High-level pipeline (concept)

```

Long Video (episode/movie)
↓
(1) Scene Detection on FULL video
↓
(2) Scene-aligned Chunking (≈30 min, never mid-scene)
↓
(3) Subtitle Parsing + Dialogue Alignment per Scene
↓
(4) Frame Sampling per Scene (multi-frame)
↓
(5) Vision Caption → Scene Title
↓
(6) Scene Scoring (cheap + explainable)
↓
(7) Local LLM Selection (under constraints)
↓
(8) FFmpeg Cut + Concat
↓
(9) Subtitle Styling + Burn-in
↓
Short-Form Output (≈3 min)

````

---

## Detailed workflow (in normal language)

### Step 1 — Scene detect the full episode first (always)
Example: you have a **54-minute episode**.

First, run scene detection on the entire episode so you get timestamps like:
- Scene 0: 00:00 → 00:52
- Scene 1: 00:52 → 01:40
- ...
- Scene N: 35:55 → 36:40

**Why this first?**
Because chunking before scene detection destroys structure. We want the *global truth* of the episode’s scene boundaries first.

---

### Step 2 — Chunk the episode WITHOUT cutting scenes
Now we want chunks around **30 minutes**, but we refuse to cut in the middle of a scene.

So we pick the **scene boundary closest to ~30 minutes**.

Example:
- One scene ends at **24 minutes**
- The next scene ends at **36 minutes**
Instead of blindly cutting at 30 minutes or always cutting “before,” we choose the boundary that best fits our chunk rule:

✅ **Nearest Scene Boundary Rule**
- Find the scene boundary closest to 30 minutes
- Allow slight overshoot if needed (configurable tolerance, e.g. +2 min)
- Never cut mid-scene (hard rule)

**Why not always cut before 30 minutes?**
Because it causes drift:
- 24 min chunk → then 30 min → then 18 min → then 36 min…
Performance becomes inconsistent and quality suffers.

This chunking strategy keeps processing predictable and scene-safe.

---

### Step 3 — Parse subtitles (SRT/VTT) and align dialogue to scenes
Instead of re-transcribing:
- parse your `.srt` / `.vtt`
- map subtitle lines into each scene based on timestamps

Each scene gets a `dialogues[]` array containing only lines inside that scene window.

**Why this is a no-brainer**
- free
- deterministic
- no extra model cost
- avoids introducing transcription errors

> Note: subtitles may be slightly offset vs video. AutoShorts supports a configurable `subtitle_offset_ms` for correction.

---

### Step 4 — Generate a scene title using a local vision model (multi-frame, not 1 frame)
For each scene:
- sample multiple frames (commonly 3 frames: 25%, 50%, 75% into the scene)
- run a local vision model to produce a caption
- optionally run a local text LLM to turn that caption into a short, punchy title

**Why 3 frames instead of a single middle screenshot?**
Single-frame can be:
- motion-blurred
- fade-to-black
- transition frame
- close-up with no context

Multi-frame sampling makes titles more reliable, which makes selection smarter.

---

## The core artifact: Scene Timeline JSON

AutoShorts builds a JSON timeline per chunk (or per episode) that looks like this:

```json
{
  "source": {
    "title": "ShowName S01E01",
    "chunk_index": 0,
    "chunk_start_sec": 0,
    "chunk_end_sec": 1800
  },
  "scenes": [
    {
      "scene_id": "c0_s12",
      "start_sec": 412.3,
      "end_sec": 468.9,
      "visual_caption": "Two detectives question a nervous man in a dim room.",
      "title": "Interrogation heats up",
      "dialogues": [
        { "start_sec": 413.1, "end_sec": 416.0, "text": "Where were you last night?" },
        { "start_sec": 416.2, "end_sec": 419.8, "text": "I already told you..." }
      ],
      "scores": {
        "dialogue_density_wps": 3.4,
        "dialogue_presence_ratio": 0.78,
        "keyword_intensity": 0.62,
        "visual_salience": 0.55,
        "length_penalty": 0.0,
        "total_score": 0.71
      }
    }
  ]
}
````

This JSON is the **single source of truth**.
Once you have it, you can:

* re-rank scenes
* change selection strategy
* generate multiple shorts
  …without reprocessing the full video again.

---

## Scene scoring & ranking (the missing piece in most pipelines)

AutoShorts does NOT just dump 200 scenes into an LLM.

That fails because:

* LLMs aren’t reliable rankers at scale
* long lists bias decisions
* you get safe but boring outputs

Instead, AutoShorts computes **cheap, explainable scores** per scene to:

* reduce noise
* surface strong candidates
* constrain what the LLM has to reason over

### What gets scored (examples)

#### 1) Dialogue density (words/sec)

Scenes with faster dialogue often contain conflict, reveals, humor, tension.

#### 2) Dialogue presence ratio

If 80% of the scene has dialogue, it’s more likely to work in Shorts than long silent filler.

#### 3) Keyword / intent markers

Simple lexicon signals like:

* questions: “why”, “what”, “how”
* conflict: “no”, “stop”, “listen”, “wait”
* urgency: “now”, “never”
  These correlate strongly with highlight moments.

#### 4) Visual salience (from vision caption)

Basic heuristics from the caption:

* number of people
* action verbs (“running”, “arguing”, “pointing”)
* strong settings (“courtroom”, “hospital”, “police station”)

#### 5) Length penalty / bonus

Scenes that are too short (<2–3s) or too long get penalized to avoid pathological selection.

### How scoring is used

Scoring does **not** decide the final output.
It is used to:

1. rank scenes
2. filter bottom-tier scenes
3. pass only top candidates to the LLM

> LLM decides the story. Scoring reduces the chaos.

---

## LLM selection (under hard constraints)

After ranking, we send only top scenes to a local LLM.

### What the LLM outputs

The LLM returns:

* scene indices (primary)
* optional trimming suggestions (secondary)
* target: total duration ≈ 3 minutes

### Hard constraints (non-negotiable)

To avoid incoherent outputs:

1. **Never cut mid-scene**
2. **Never start/end mid-subtitle**
3. **Trimming is only allowed at subtitle boundaries**
4. **Prefer whole scenes whenever possible**
5. **Total duration must land near the target** (e.g. 170–190 seconds)

This prevents:

* mid-sentence cuts
* “clip salad”
* awkward pacing

> LLM picks *what*. The system enforces *how*.

---

## Clip assembly & subtitle styling

Once we have the selection plan:

1. **Cut segments** using FFmpeg (source-of-truth timestamps)
2. **Concatenate** selected clips
3. **Rebuild subtitles** only for selected dialogue lines
4. **Style subtitles** (recommended: ASS format for consistent font/outline/position)
5. **Burn-in subtitles** and export final output

Why FFmpeg is the backbone:

* fast
* deterministic
* hardware-accelerated where possible
* battle-tested

Python orchestrates. FFmpeg edits.

---

## Practical issues AutoShorts is designed to handle (the “7 fixes”)

AutoShorts includes design choices to avoid common failure modes:

1. **Scene detection ≠ semantic beats**
   → includes a merge pass for micro-scenes (very short shots)

2. **Chunking drift**
   → nearest-boundary chunking + overshoot tolerance

3. **Subtitle mismatch / offset**
   → supports configurable subtitle offset correction

4. **Single-frame vision errors**
   → multi-frame sampling (25%, 50%, 75%)

5. **LLM choosing arbitrary timestamp cuts**
   → LLM selects scenes; trimming only at subtitle boundaries

6. **Subtitle styling inconsistency**
   → ASS-based subtitle styling for reliable rendering

7. **Boring outputs at scale**
   → scoring layer + ranking + LLM story selection

---

## What AutoShorts is (and is not)

### AutoShorts is:

* a structured video understanding pipeline
* local-first and inspectable
* designed for throughput + iteration

### AutoShorts is not:

* a guarantee of virality
* a “one-click money machine”
* a cloud SaaS

It’s a toolkit and a system architecture you can extend.

---

## Who this is for

* builders exploring **AI + media tooling**
* engineers who value **local workflows**
* creators experimenting with scalable clip generation
* anyone who wants **auditability** instead of black-box outputs

---

## Open-source philosophy

AutoShorts is intentionally:

* modular
* replaceable at every stage
* easy to fork and experiment with

Swap the scene detector.
Swap the vision model.
Adjust scoring weights.
Try new selection prompts.
Add analytics.

The architecture is designed to invite contributions.

---

## Final thought

Most AI video tools start with a model.

**AutoShorts starts with structure.**

Once structure exists, intelligence becomes cheap — and quality becomes repeatable.

That’s the bet this project makes.
