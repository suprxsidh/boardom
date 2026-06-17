# Adding a New Channel

## What you need to do (2 minutes)
1. Create a Gmail for the channel (e.g. `historychannel@gmail.com`)
2. Go to [youtube.com](https://youtube.com), sign in with that Gmail, click your avatar → **Create a channel**

## What the script does automatically
Run this one command:
```bash
cd "/Users/Suprasidh/YT Automator 2.0"
.venv/bin/yta provision-channel <channel_name> <gmail>

# Examples:
.venv/bin/yta provision-channel history historychannel@gmail.com
.venv/bin/yta provision-channel space spacechannel@gmail.com
```

The script will:
1. Install `gcloud` CLI if missing (via Homebrew)
2. Open a browser → sign into Google Cloud with your channel Gmail (one time per account)
3. Create a GCP project automatically
4. Enable YouTube Data API v3 automatically
5. Open GCP Console and fill out the OAuth consent screen automatically
6. Create Desktop app credentials and download the JSON automatically
7. Wire up the `channels/<name>/` directory
8. Open a browser for YouTube upload permission → approve it
9. Done — channel is live

## If Playwright automation fails (fallback)
The script will print the exact URLs and pause. Do these 2 steps manually (takes ~3 minutes):

**Step A — OAuth consent screen:**
1. Go to the URL the script prints (direct link to your project's consent screen)
2. Select **External** → Create
3. Fill in: App name (anything), Support email (your Gmail), Developer email (your Gmail)
4. Click through Scopes (skip), add your Gmail as a Test user, Save
5. Press Enter in the terminal to continue

**Step B — Create credentials:**
1. Go to the URL the script prints (direct link to Credentials page)
2. Click **+ Create Credentials → OAuth client ID**
3. Application type: **Desktop app** → Create
4. Click **Download JSON**
5. Paste the file path when the script asks

The script then continues automatically and finishes the setup.

## If you already have a credentials JSON (manual path)
If you set up GCP yourself and have the JSON, skip `provision-channel` and use:
```bash
.venv/bin/yta setup-channel <name> <email> ~/Downloads/client_secret_*.json
```

## Verify it worked
```bash
.venv/bin/yta doctor               # shows all channels + status
.venv/bin/yta run <name> --dry-run # test without uploading
.venv/bin/yta run <name> --count 1 # go live
```

## Channel configs
Each channel's content strategy lives in `channels/<name>/config.json`.
After provisioning, review and customise:
- `content_strategies` — the themes the LLM picks from
- `prompt_profile.system_role` — the narrator persona
- `prompt_profile.script_rules` — script structure and style constraints

Pre-built configs exist for: `biology`, `history`, `physics`, `finance`, `psychology`, `ai_tech`, `space`
