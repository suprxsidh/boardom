# CLAUDE.md — YT Automator 2.0

## What This Is
Automated YouTube Shorts pipeline. Generates scripts via Gemini, synthesizes TTS with edge-tts, transcribes with Whisper, fetches Pexels video clips, renders subtitles frame-by-frame via PIL→ffmpeg pipe, and uploads to YouTube via Data API v3.

## Key Commands
```bash
# Run pipeline for one channel (1 video, real upload)
.venv/bin/yta run biology --count 1

# Dry run (skips upload, saves video to outputs/)
.venv/bin/yta run biology --count 1 --dry-run

# Run all channels
.venv/bin/yta run --count 1

# Health check
.venv/bin/yta doctor
```

## Project Structure
```
channels/
  biology/
    config.json              # Channel config (prompts, strategies)
    credentials.json         # OAuth Desktop app credentials (gitignored)
    token.json               # Auto-created after first auth (gitignored)
    topics.txt               # Topic history (avoids repeats)
    outputs/                 # Generated videos for this channel

config/
  app_settings.json          # Gemini model, Whisper model, TTS voices
  media_sources.json         # Provider priority (Pexels first, then Pixabay)

assets/music/               # Shared bg music (bg1.mp3–bg4.mp3, must be > video duration)
data/runs/                  # Daily JSONL run logs (all channels)
data/optimizer/             # Bandit arm weights per channel

src/yt_automator/
  pipeline/
    orchestrator.py          # Main pipeline coordinator
    content_generator.py     # Gemini/Ollama script generation
    tts_engine.py            # edge-tts synthesis (rate +30%)
    subtitles.py             # Whisper transcription + ASS file + STT correction
    video_renderer.py        # PIL frame rendering → ffmpeg pipe (no libass needed)
    media_sourcer.py         # Fetches assets from providers
    youtube_client.py        # OAuth2 + YouTube Data API v3 upload
  providers/
    pexels_provider.py       # Primary: portrait video clips (parallel download)
    pixabay_provider.py      # Fallback: images (query capped at 100 chars)
    wikimedia_provider.py    # Fallback: images
  optimizer/
    bandit_optimizer.py      # Epsilon-greedy strategy selection
```

## Adding a New Channel
1. `mkdir -p channels/<name>/outputs`
2. Copy an existing `channels/biology/config.json` → `channels/<name>/config.json`, update all fields
3. Create a personal Gmail for that channel (not Workspace)
4. Create a YouTube channel on that Gmail (youtube.com → avatar → Create channel)
5. Create a GCP project logged in as that Gmail — enable YouTube Data API v3, OAuth consent (External, add Gmail as test user), Desktop app credentials
6. Download credentials JSON → `channels/<name>/credentials.json`
7. Run: `.venv/bin/yta run <name> --count 1` — browser opens for OAuth on first run

## Environment (.env)
```
GEMINI_API_KEY=...
PEXELS_API_KEY=...
PIXABAY_API_KEY=...      # optional fallback
```

## Key Technical Facts
- **ffmpeg**: Homebrew build lacks libass + libfreetype — subtitles are rendered via PIL per-frame, raw RGB piped to ffmpeg. Never use `ass` or `drawtext` filters.
- **Font**: Impact at 110px, center screen, pop-in animation 0.8→1.0 over 0.2s per word. Font path: `/Library/Fonts/Impact.ttf`
- **Clips**: 5 Pexels portrait clips stitched with equal time split, 1.2× saturation
- **TTS rate**: +30% via edge-tts
- **STT correction**: Whisper output aligned against original script via `difflib.SequenceMatcher` to fix mis-hearings without changing timing
- **Music**: Selected by probing duration with ffprobe — must be ≥ voice duration
- **Gemini model**: `gemini-2.5-flash` (set in app_settings.json)
- **Whisper model**: `tiny.en` — FP32 on CPU (FP16 warning is harmless, ignore it)

## YouTube Auth — Common Issues
- `youtubeSignupRequired`: The authenticated Google account has no YouTube channel. Create one at youtube.com first.
- `403 forbidden / org restriction`: Workspace accounts often block YouTube API. Use personal Gmail instead.
- Stale token: `rm secrets/youtube/<channel>_token.json` then re-run.
- Each channel should have its own Gmail + GCP project for clean isolation.

## LLM Prompt Rules (enforced in content_generator.py + channel configs)
Scripts must be raw spoken narration only:
- No structural labels (Hook, CTA, Intro, Outro)
- No visual references ("as you can see", "look at this", "on screen")
- Every sentence must work with eyes closed (audio-only comprehensible)
- 120–160 words

## Channel Configs (current)
- `biology.json` — 10 strategies, deep ocean / microbiome / parasites / neuroscience / de-extinction
- `physics.json` — 8 strategies, quantum / relativity / materials science / optics
- `history.json` — 9 strategies, forgotten figures / secret history / failed empires / tech history
- `finance.json` — 8 strategies (needs credentials setup before use)
- `psychology.json` — 8 strategies (needs credentials setup before use)
- `ai_tech.json` — 8 strategies (needs credentials setup before use)

## Content Strategy System
Each channel has `content_strategies` (dict of themes). `BanditOptimizer` uses epsilon-greedy (ε=0.2) to pick which strategy to use each run, learning from upload performance over time. Record rewards manually: `.venv/bin/yta reward <channel> <strategy_key> <0.0-1.0>`
