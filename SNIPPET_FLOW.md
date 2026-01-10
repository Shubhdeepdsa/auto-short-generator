# Snippet Dev Flow (ep001_snip)

These commands use your existing files:

- Full movie input: `og_test_files/Tenet.mp4`
- Full subtitles: `og_test_files/Tenet-English.srt`
- Snippet video: `snippets/ep001_snip.mp4`

## 0) Create a 10-minute video snippet

```bash
mkdir -p snippets
ffmpeg -y -i og_test_files/Tenet.mp4 -ss 00:00:00 -t 600 -c copy snippets/ep001_snip.mp4
```

## 1) Init the snippet episode

```bash
uv run auto init --episode-id ep001_snip --series-id seriesA
```

## 2) Trim full subtitles to the first 10 minutes

```bash
uv run auto subtitles-trim \
  --input og_test_files/Tenet-English.srt \
  --output artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt \
  --end-sec 600
```

## 3) Run the full pipeline (detect + merge + chunk + timeline)

```bash
uv run auto pipeline \
  --video snippets/ep001_snip.mp4 \
  --series-id seriesA \
  --episode-id ep001_snip \
  --thumbs \
  --merged-thumbs \
  --subtitle artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt
```

## 4) Run each step separately (same outputs as pipeline)

```bash
uv run auto scene-detect --video snippets/ep001_snip.mp4 --series-id seriesA --episode-id ep001_snip --thumbs
uv run auto scene-merge --series-id seriesA --episode-id ep001_snip --merged-thumbs --video snippets/ep001_snip.mp4
uv run auto chunk --series-id seriesA --episode-id ep001_snip --target-sec 600 --tolerance-sec 60
uv run auto extract-frames --video snippets/ep001_snip.mp4 --series-id seriesA --episode-id ep001_snip
uv run auto timeline --series-id seriesA --episode-id ep001_snip --subtitle artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt
```

## 5) Generate vision captions + titles (optional)

```bash
uv sync --extra vision
uv run auto vision --series-id seriesA --episode-id ep001_snip
```

## 6) Score scenes (optional, Ollama)

```bash
ollama serve
ollama pull llama3.2:3b
uv run auto score-scenes --series-id seriesA --episode-id ep001_snip
```

## 7) Quick checks

```bash
ls -la artifacts/seriesA/ep001_snip/scenes
ls -la artifacts/seriesA/ep001_snip/chunks
ls -la artifacts/seriesA/ep001_snip/timeline
ls -la artifacts/seriesA/ep001_snip/frames
uv run auto chunk-summary --series-id seriesA --episode-id ep001_snip
uv run auto frames-summary --series-id seriesA --episode-id ep001_snip
```

## Optional overrides (dev snippets)

If you want to tweak chunking or subtitle offset per run:

```bash
uv run auto pipeline \
  --video snippets/ep001_snip.mp4 \
  --series-id seriesA \
  --episode-id ep001_snip \
  --thumbs \
  --merged-thumbs \
  --subtitle artifacts/seriesA/ep001_snip/input/Tenet-English-snippet.srt \
  --target-sec 600 \
  --tolerance-sec 60 \
  --subtitle-offset-ms 0
```
