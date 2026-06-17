from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


_CHANNEL_TEMPLATES = {
    "science": "biology",
    "space": "space",
    "history": "history",
    "finance": "finance",
    "psychology": "psychology",
    "ai_tech": "ai_tech",
    "biology": "biology",
    "physics": "physics",
}

_DEFAULT_CONFIG = {
    "youtube": {
        "category_id": "27",
        "privacy_status": "public",
        "timezone": "Asia/Kolkata",
        "daily_slots": ["17:30", "19:00", "20:30", "22:00", "23:30"],
    },
    "pipeline": {"assets_per_video": 5},
    "rl_profile": {"epsilon": 0.2},
    "content_strategies": {
        "strategy_1": {
            "theme": "Edit this: a counterintuitive fact about your niche topic",
            "default_query": "abstract background nature",
        }
    },
    "prompt_profile": {
        "system_role": "Edit this: You are a viral narrator for this channel.",
        "script_rules": (
            "Write 120 to 160 words of spoken narration. Open with a bold specific statement. "
            "Build to a surprising payoff. Close with one line that makes the listener think. "
            "No labels, headers, or section names. No visual references. Every sentence works "
            "with eyes closed. BANNED: very, basically, essentially, fascinating, amazing."
        ),
    },
}


def setup_channel(
    repo_root: Path,
    channel_name: str,
    email: str,
    credentials_src: Path,
    template: str | None = None,
) -> None:
    ch_dir = repo_root / "channels" / channel_name

    # ── 1. Create directory structure ────────────────────────────────────
    print(f"\n[1/4] Creating channel directory: channels/{channel_name}/")
    (ch_dir / "outputs").mkdir(parents=True, exist_ok=True)

    # ── 2. Place credentials ─────────────────────────────────────────────
    print(f"[2/4] Copying credentials from {credentials_src}")
    dest = ch_dir / "credentials.json"
    shutil.copy2(credentials_src, dest)
    dest.chmod(0o600)
    print(f"      → channels/{channel_name}/credentials.json")

    # ── 3. Create config ─────────────────────────────────────────────────
    config_path = ch_dir / "config.json"
    if config_path.exists():
        print(f"[3/4] Config already exists — skipping (edit manually if needed)")
    else:
        template_name = template or _pick_template(repo_root, channel_name)
        template_path = repo_root / "channels" / template_name / "config.json"

        if template_path.exists():
            print(f"[3/4] Creating config from template: channels/{template_name}/")
            cfg = json.loads(template_path.read_text())
            cfg["channel_name"] = channel_name
            cfg["youtube"].pop("credentials_file", None)
            cfg["youtube"].pop("token_file", None)
            cfg.pop("paths", None)
        else:
            print(f"[3/4] Creating blank config (edit channels/{channel_name}/config.json before running)")
            cfg = {"channel_name": channel_name, **_DEFAULT_CONFIG}

        config_path.write_text(json.dumps(cfg, indent=2))
        print(f"      → channels/{channel_name}/config.json")
        print(f"      ⚠  Review and update content_strategies + prompt_profile for this channel")

    # ── 4. OAuth flow ─────────────────────────────────────────────────────
    print(f"\n[4/4] Running YouTube OAuth flow for {email}")
    print("      A browser window will open — sign in with:", email)
    print("      Grant the youtube.upload permission when prompted.\n")

    token_path = ch_dir / "token.json"
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        flow = InstalledAppFlow.from_client_secrets_file(str(dest), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
        token_path.chmod(0o600)
        print(f"\n[OK] Token saved → channels/{channel_name}/token.json")
    except Exception as exc:
        print(f"\n[FAIL] OAuth failed: {exc}")
        print(f"       Run 'yta run {channel_name} --dry-run' to retry on next use.")
        return

    # ── Done ──────────────────────────────────────────────────────────────
    print(f"""
✓ Channel '{channel_name}' is ready.

Next steps:
  1. Review config:  channels/{channel_name}/config.json
  2. Test dry run:   .venv/bin/yta run {channel_name} --dry-run
  3. Go live:        .venv/bin/yta run {channel_name} --count 1
""")


def _pick_template(repo_root: Path, channel_name: str) -> str:
    """Return name of best existing channel to use as config template."""
    channels_dir = repo_root / "channels"
    existing = [
        p.name for p in channels_dir.iterdir()
        if p.is_dir() and (p / "config.json").exists()
    ]
    if channel_name in _CHANNEL_TEMPLATES:
        preferred = _CHANNEL_TEMPLATES[channel_name]
        if preferred in existing:
            return preferred
    return existing[0] if existing else ""
