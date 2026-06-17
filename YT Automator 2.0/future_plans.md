# Future Plans — YT Automator 2.0

## 1. GCP Setup Automation Script

**Goal:** Given a Gmail account, auto-provision a GCP project ready for YouTube uploads — no manual browser steps.

**What's automatable (~90%):**
- Project creation via `gcloud projects create` or Python Resource Manager API
- Enable YouTube Data API v3 via `gcloud services enable youtube.googleapis.com`
- Download OAuth credentials JSON programmatically

**Hard blocker — OAuth consent screen:**
- No REST API or Terraform support exists for this (confirmed open GitHub issue in terraform-provider-google)
- Requires manual browser step once per project
- Workaround options:
  - Selenium/Puppeteer to automate consent screen setup (fragile, breaks on UI changes)
  - Maintain a "template" GCP project with consent screen pre-configured; clone for new channels

**YouTube channel creation automation:**
- No YouTube Data API endpoint exists for creating a channel — it's browser-only
- Only option: Playwright browser automation (navigate to youtube.com → sign in → Create channel)
- Risk: Google bot detection on sign-in makes this unreliable; fragile to UI changes
- Pragmatic approach: automate everything else, keep channel creation as a one-time 30-second manual step

**Recommended approach:**
1. Python script wrapping `gcloud` CLI: create project → enable API → create Desktop OAuth client
2. Pause and prompt user to complete OAuth consent screen + YouTube channel creation manually (print step-by-step instructions)
3. Script resumes: downloads credentials, places them in `secrets/youtube/<channel>_credentials.json`
4. Script triggers first OAuth flow, saves token

**Implementation:** `scripts/setup_channel.py --channel <name> --email <gmail>`


---

## 2. Trend Analysis & Prompt Optimisation

**Research findings (2025–2026):**

**Hooks that work:**
- Movement or visual change in the very first frame (never start static)
- Bold text overlay within the first frame
- Shock stat or counterintuitive claim — answer delivered within 30 seconds
- "Why [thing everyone knows] is actually [totally different]" framing
- News-anchoring: tie topic to a trending event for extra discovery

**What's oversaturated:** Generic "Top 10" lists, repetitive formats with no variation

**Content angles to pursue:**
- Fact-checking viral science misconceptions
- "Why [event] is actually happening" explanations
- Everyday phenomena explained from first principles

**Prompt improvements to implement:**
- Add "open with a visual change word" instruction — first word should invoke movement or surprise
- Inject trending hook templates into the system role per channel
- Add a `hook_style` field to content strategies so the bandit can test which hooks perform best
- A/B test 15-35 sec vs 45-60 sec script lengths via strategy variants

**Posting strategy:** 3–5 videos/week; Tuesday–Thursday 6–9 PM local time performs best


---

## 3. AI Detection Avoidance

**What YouTube flags (2026):**
- High upload frequency + identical format + generic TTS + stock footage reuse = "inauthentic" signal
- Photorealistic AI faces/voice cloning of real people → mandatory disclosure + removal risk
- Mass-produced templated content with minimal editing

**What's safe:**
- AI voiceover on educational content is fully monetizable if content is original
- YouTube labels AI content informationally (not algorithmically punished) as of May 2026
- Edge-tts voices are fine; they're not cloning real people

**Adjustments to make:**
- Vary clip order, pacing, and number of clips per video (don't always use 5)
- Randomise TTS voice per video (already partially done via `random.choice(voices)`)
- Vary subtitle style occasionally (size, position offset)
- Introduce Manim-generated animation clips to break stock footage monotony
- Avoid uploading more than 3–4 videos/day per channel


---

## 4. Alternative Video Sources (Pexels Replacement)

**Priority 1 — Free, implement soon:**
- **Pixabay Video API** — already integrated as fallback for images; extend to video. Free, decent science stock, portrait support
- **Manim** — Python library for animated science diagrams. Generate animated backgrounds (cells, DNA, atoms, equations, graphs). Native 9:16 output. Zero cost. Eliminates the "same stock footage every video" problem. ~2–3 weeks to integrate

**Priority 2 — Medium term:**
- **NASA API** — Free public domain space/astronomy footage and images. JSON API access. Perfect for a space channel. Crop to 9:16 as needed. ~1 week to integrate

**Priority 3 — Later, if budget allows:**
- **Kling AI API** — Text-to-video, native 9:16, ~$10–20/month for moderate volume. Best value AI video gen option. ~4–6 hours to integrate once API access obtained

**Avoid:**
- Sora — shutting down Sept 2026
- Runway ML — expensive, no free tier worth using
- Coverr/Videvo — no public API

**Implementation path:** Add `ManimProvider` and `NasaProvider` to `src/yt_automator/providers/`. Both slot into the existing `MediaSourcer` provider chain.


---

## 5. Scaling to New Channels

**Current channels:** biology, history, physics
**Easy to add:** space/astronomy, chemistry, psychology, mathematics, geography, ancient civilizations

**Steps to add a channel (current process — ~20 min):**
1. Create Gmail for the channel
2. Create YouTube channel on that Gmail
3. Create GCP project (manual), enable YouTube API, configure OAuth consent, download credentials
4. Create `config/channels/<name>.json` (copy existing, update prompts + strategies)
5. Drop credentials in `secrets/youtube/`
6. Run

**Future (after GCP automation script):** Steps 2–4 collapse to one command


---

## 6. Content Strategy Per Channel

**Biology** (current): Deep ocean creatures, microbiome, human body oddities, plant signals, evolution
- Gap to fill: parasite behaviour, bioluminescence, neurological quirks

**Physics** (current): Quantum, relativity, thermodynamics, astrophysics, classical mechanics
- Gap to fill: materials science, optics, acoustics

**History** (current): Forgotten figures, turning points, daily life, misconceptions, firsts
- Gap to fill: secret societies, failed empires, technology history

**Planned channels:**
- **Space** — black holes, exoplanets, Mars missions, dark matter, Fermi paradox
- **Psychology** — cognitive biases, social experiments, memory, decision making
- **Chemistry** — everyday chemical reactions, food science, dangerous elements

**Bandit feedback loop:** After 30+ uploads per channel, analyse which `content_strategies` keys have highest average view count. Use `.venv/bin/yta reward` to feed signals back to `BanditOptimizer`.


---

## 7. Reddit Story Narration (Skipped — Legal Risk)

Reddit posts are copyrighted by their authors. Narrating them without permission risks DMCA takedowns and demonetization. Fair use arguments exist but are fragile. Skip as a primary niche. If revisited: transform the content significantly, add original commentary, never read verbatim. Best to build original content niches instead.

---

## 8. Anti-AI-Slop Measures (Partially Implemented)

**Already implemented:**
- Structure randomization: prompt randomly picks hook_first / cold_open / jump_to_value per video
- Banned phrase list in prompt (AI marketing verbs, passive voice patterns, filler words)
- Temperature 1.1 + top_p 0.95 for more varied output
- Structural variation in channel configs

**Still to implement:**
- **Clip repetition tracker**: flag if same Pexels clip appears across multiple recent videos
- **TTS prosody variation**: Coqui TTS (open-source, self-hosted) with ±2-3% speed variation per sentence and ±5-8% pitch on high-impact words. Edge-tts at fixed +30% sounds robotic at scale.
- **Color grading randomization**: vary saturation/contrast slightly per video in video_renderer.py (`eq=saturation=X` where X randomly varies 1.1–1.4)
- **Upload cadence cap**: never more than 2 videos/day per channel
- **Title humanization**: inject one colloquial or punchy phrase into title generation rather than keyword-only titles

**What YouTube flags as of Jan 2026:**
- High frequency + identical format + TTS + same stock footage = "inauthentic"
- Voice cloning of real people without disclosure → removal
- Templated mass-produced content with no variation → suppressed
- Safe: educational AI voiceover + original scripts + varied structure + genuine perspective

---

## 9. RL Feedback Loop — Analytics-Driven Content Optimisation

### Goal
Close the loop between upload and content generation: automatically observe what performs, feed the signal back to the strategy selector, and let the system drift toward what works over time — without manual intervention.

### What to Measure (Reward Signals)
YouTube Analytics API provides these metrics 24-48h after upload:

| Metric | Signal type | Notes |
|--------|-------------|-------|
| `averageViewDuration` / `averageViewPercentage` | **Primary** | Best proxy for content quality in the algorithm |
| `views` (first 48h) | Secondary | Volume signal, biased by upload time |
| `likes` / `comments` | Engagement | Comment count especially = topic resonance |
| `subscribersGained` | Long-term | Good for tracking whether a strategy grows the channel |
| `impressionClickThroughRate` | Title/thumbnail | Decouples discovery from retention |

**Composite reward formula (suggested):**
```
reward = 0.5 × (avg_view_pct / 100)
       + 0.3 × clip(views_48h / target_views, 0, 1)
       + 0.2 × clip(likes / views_48h, 0, 1)
```
Normalise all terms to [0, 1]. Weight retention highest because it's the strongest algorithm signal and hardest to fake.

### The Loop Architecture

```
Upload video
  → wait 48h (cron job)
  → pull Analytics API for that video_id
  → compute composite reward
  → call BanditOptimizer.record_reward(channel, strategy_key, reward)
  → BanditOptimizer adjusts arm weights (epsilon-greedy already in place)
  → next run picks strategy based on updated weights
```

### What the Bandit Already Does
`BanditOptimizer` in `src/yt_automator/optimizer/bandit_optimizer.py` already implements epsilon-greedy arm selection per channel. It stores per-arm counts and value estimates in `data/optimizer/bandit_state.json`. Currently only manual rewards via `yta reward` CLI. The RL loop just automates the reward ingestion.

### Implementation Plan

**1. YouTube Analytics poller** (`src/yt_automator/analytics/analytics_poller.py`):
- OAuth scope needed: add `youtube.readonly` to the existing flow
- Call `youtubeAnalytics.reports.query` with `metrics=views,averageViewDuration,likes,comments,subscribersGained` for each video_id
- Store raw metrics in `channels/<name>/analytics/<video_id>.json`

**2. Run log enrichment** (`data/runs/<date>.jsonl`):
- Each run record already stores `video_id`. Add `analytics_collected: false` flag
- Poller scans for records where flag is false AND upload was >48h ago

**3. Reward computation** (`src/yt_automator/analytics/reward.py`):
- Normalise metrics against rolling channel average (not global constants — channels vary wildly)
- First 10 videos: use uniform priors so the bandit explores before exploiting

**4. Cron integration**:
- Add a `yta analytics` CLI command that runs the poller + reward updater
- Schedule daily via launchd or cron: `0 6 * * * cd /path && .venv/bin/yta analytics`

**5. Prompt parameter adaptation (stretch goal)**:
- Beyond strategy selection, track which `structure_variant` (hook_first / cold_open / jump_to_value) correlates with higher retention per channel
- Store structure variant in run log → feed as a second bandit dimension
- Long term: adapt temperature, word count target, hook length based on what retains viewers

### Delayed Reward Problem
Views accumulate over days/weeks. A naive 48h window misses late-breaking viral videos. Solutions:
- **Two-stage reward**: preliminary reward at 48h (50% weight), final reward at 7d (50% weight)
- **Discounted update**: apply smaller learning rate to preliminary rewards
- Start simple: 48h only, revisit if bandit shows instability

### Key Files to Create
```
src/yt_automator/analytics/
  analytics_poller.py     # pulls YouTube Analytics API
  reward.py               # computes normalised composite reward
src/yt_automator/cli.py   # add `yta analytics` command
channels/<name>/
  analytics/              # per-video raw JSON responses
```

### OAuth Scope Change Required
Current scope: `youtube.upload` only. Need to add:
- `https://www.googleapis.com/auth/youtube.readonly` (channel data)
- `https://www.googleapis.com/auth/yt-analytics.readonly` (analytics)

This requires deleting existing tokens and re-authorising. Plan to do this when implementing.

---

## 10. Misc Infrastructure

- **Monitoring dashboard** — simple Flask/Streamlit page showing upload history, view counts per strategy, bandit weights
- **Scheduled runs** — cron job or launchd plist to trigger `yta run --all` daily at optimal times
- **Thumbnail generation** — auto-generate thumbnails with PIL (bold text + blurred background frame from video)
- **Analytics ingestion** — pull YouTube Analytics API stats 48h after upload → feed as reward to bandit
- **Multi-language channels** — edge-tts supports 40+ languages; same pipeline could serve Spanish/Hindi science channels
