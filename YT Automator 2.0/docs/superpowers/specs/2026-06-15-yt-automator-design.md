# YT Automator 2.0 — Design Spec

**Date:** 2026-06-15  
**Status:** Approved

---

## Goal

Port the `youtube-automator` v2 reference codebase into `YT Automator 2.0/`, fix known bugs, upgrade the Gemini client, and wire up 3 channels (biology, physics, history). The result is a self-contained CLI tool that generates YouTube Shorts end-to-end and uploads them on a schedule.

---

## Channels in scope

| Channel | Category ID | Niche |
|---------|-------------|-------|
| biology | 27 | Deep ocean, human body, evolution |
| physics | 27 | Counterintuitive physics, space science |
| history | 27 | Historical deep-dives, forgotten stories |

All channels use Asia/Kolkata timezone, 5 daily slots (17:30, 19:00, 20:30, 22:00, 23:30).

---

## Architecture

Single Python package (`yt_automator`) installed via `pip install -e .`. Entry point: `yta` CLI.

Pipeline per video (orchestrated by `PipelineOrchestrator.run_once`):

```
pick strategy (epsilon-greedy bandit)
  → generate content (Gemini API → JSON: topic/script/title/tags)
  → QA gate (word count, title length)
  → TTS (edge-tts → voice.mp3)
  → subtitles (Whisper tiny.en → subs.ass)
  → fetch image (Pixabay / Wikimedia / NASA)
  → render video (ffmpeg: image + voice + music + burned subtitles → final.mp4)
  → upload (YouTube Data API v3 OAuth2)
  → log (JSONL)
```

---

## Directory Structure

```
YT Automator 2.0/
├── src/yt_automator/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── secrets.py
│   ├── pipeline/           orchestrator, content_generator, tts_engine,
│   │                       subtitles, media_sourcer, video_renderer,
│   │                       youtube_client, run_logger, qa
│   ├── providers/          base, pixabay, wikimedia, nasa
│   ├── optimizer/          bandit_optimizer (epsilon-greedy)
│   └── utils/              paths, text, time_utils
├── config/
│   ├── app_settings.json
│   ├── media_sources.json
│   └── channels/           biology.json, physics.json, history.json
├── assets/music/           bg1–bg4.mp3 (user-supplied, gitignored)
├── secrets/youtube/        *_credentials.json (user-supplied, gitignored)
├── data/history/           per-channel topic dedup
├── data/runs/              JSONL publish log
├── data/optimizer/         bandit state
├── outputs/                rendered videos (gitignored)
├── tests/
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
└── SETUP.md
```

---

## Bug Fixes

| Bug | Fix |
|-----|-----|
| `google-generativeai` imported but absent from `pyproject.toml` | Replace with `google-genai>=1.0.0` throughout |
| `yt-dlp` and `wikipedia-api` listed as deps but never used | Remove from `pyproject.toml` |
| `get_repo_root()` counts parent path depth — fragile if folder moves | Replace with sentinel file (`.yta-root`) at project root |
| Subtitle ASS `Alignment=5` + `MarginV=860` places text mid-screen | Fix to `Alignment=2` (bottom-center) + `MarginV=120` for Shorts |

---

## Improvements (Approach B)

| Item | Detail |
|------|--------|
| `google-genai` SDK | Updated `ContentGenerator` to use `google.genai.Client` instead of deprecated `google.generativeai` |
| `.gitignore` | Excludes `secrets/`, `outputs/`, `.env`, `data/runs/`, `data/optimizer/`, `assets/music/`, `__pycache__`, `.venv` |
| `Makefile` | `make setup`, `make doctor`, `make run CHANNEL=biology`, `make daemon-all`, `make dry-run` |
| `.env.example` | Every key documented with where-to-get-it comments |
| `SETUP.md` | Step-by-step guide: brew install ffmpeg, get keys, create Google Cloud project, OAuth setup, first run |

---

## Content Generation (Gemini)

- Primary: `google-genai` SDK, model `gemini-2.0-flash-lite` (free tier generous)
- Fallback: Ollama (optional, controlled by `OLLAMA_MODEL` env var)
- Final fallback: hardcoded template scripts (no API needed)
- Prompt returns strict JSON: `topic, script, title, description, video_query, tags, source_links`

---

## Media Providers

| Provider | Enabled for | Key required |
|----------|-------------|-------------|
| Pixabay | all channels | `PIXABAY_API_KEY` (free) |
| Wikimedia | all channels | none |
| NASA | physics only | `NASA_API_KEY` (free, optional — falls back to DEMO_KEY) |

---

## YouTube Upload

- OAuth2 desktop flow per channel
- Credentials: `secrets/youtube/<channel>_credentials.json`
- Token auto-refreshed; first run opens browser for consent
- Supports `privacy_status: public` or scheduled publish via `publishAt`

---

## Scheduler / CLI

```bash
yta list-channels
yta run biology --count 1 --dry-run
yta run-all --count 1 --dry-run
yta daemon biology
yta daemon-all --run-now
yta doctor
yta record-reward biology deep_ocean 0.5
```

---

## Optimiser

Epsilon-greedy bandit (`BanditOptimizer`) picks content strategy per channel. State persisted in `data/optimizer/bandit_state.json`. Manual reward feedback via `yta record-reward`.

---

## Out of Scope

- Video footage (only still images with Ken Burns zoom effect)
- Thumbnail generation
- Analytics ingestion / automatic reward signals
- reddit_dilemma, tooltok, factsprint, money_basics, career_script_lab channels (can be added later by dropping a JSON into `config/channels/`)
