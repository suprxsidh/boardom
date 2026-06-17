"""
Full channel provisioning — from Gmail to upload-ready in one command.

Flow:
  1. Check / install gcloud CLI
  2. gcloud auth login (browser opens once — user signs in with channel Gmail)
  3. Create GCP project via gcloud
  4. Enable YouTube Data API v3 via gcloud
  5. Playwright: open GCP Console, configure OAuth consent screen
  6. Playwright: create Desktop app OAuth credentials, download JSON
  7. Call setup_channel() to wire up directory + run YouTube OAuth

Usage:
  yta provision-channel <channel_name> <gmail>
  e.g.  yta provision-channel history history@gmail.com
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from yt_automator.pipeline.channel_setup import setup_channel


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True, capture: bool = False, **kw):
    if capture:
        return subprocess.run(cmd, check=check, capture_output=True, text=True, **kw)
    return subprocess.run(cmd, check=check, **kw)


def _gcloud(*args, account: str | None = None) -> subprocess.CompletedProcess:
    base = [shutil.which("gcloud") or "gcloud"]
    if account:
        base += ["--account", account]
    return _run(base + list(args), capture=True)


def _ensure_gcloud() -> None:
    if shutil.which("gcloud"):
        return
    print("[INFO] gcloud CLI not found. Installing via Homebrew...")
    if not shutil.which("brew"):
        print("[FAIL] Homebrew not found. Install gcloud manually: https://cloud.google.com/sdk/docs/install")
        raise SystemExit(1)
    _run(["brew", "install", "--cask", "google-cloud-sdk"])
    if not shutil.which("gcloud"):
        print("[FAIL] gcloud install failed. Install manually and re-run.")
        raise SystemExit(1)
    print("[OK] gcloud installed")


def _ensure_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("[INFO] Installing playwright...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright"],
            check=True, stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            check=True,
        )
        print("[OK] Playwright installed")


def _project_id(channel_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "-", channel_name.lower())[:20]
    return f"yta-{slug}-{int(time.time()) % 100000}"


# ── main entry ────────────────────────────────────────────────────────────────

def provision_channel(repo_root: Path, channel_name: str, email: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Provisioning channel: {channel_name} ({email})")
    print(f"{'='*60}\n")

    _ensure_gcloud()
    _ensure_playwright()

    project_id = _project_id(channel_name)

    # ── Step 1: gcloud auth ───────────────────────────────────────────────
    print("[1/5] Authenticating with Google Cloud...")
    print(f"      A browser will open — sign in with: {email}")
    print("      (This is a one-time step for this Gmail account)\n")

    result = _gcloud("auth", "list", "--format=value(account)", account=email)
    already_authed = email in result.stdout

    if not already_authed:
        _run([shutil.which("gcloud"), "auth", "login", "--account", email,
              "--no-launch-browser"], capture=False)
    else:
        print(f"      Already authenticated as {email}")

    # ── Step 2: Create project ────────────────────────────────────────────
    print(f"\n[2/5] Creating GCP project: {project_id}")
    result = _gcloud("projects", "create", project_id,
                     f"--name=yt-automator-{channel_name}",
                     account=email)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"[FAIL] Could not create project: {result.stderr}")
        raise SystemExit(1)
    print(f"      [OK] Project: {project_id}")

    # ── Step 3: Enable YouTube Data API v3 ───────────────────────────────
    print(f"\n[3/5] Enabling YouTube Data API v3...")
    result = _gcloud("services", "enable", "youtube.googleapis.com",
                     f"--project={project_id}", account=email)
    if result.returncode != 0:
        print(f"[WARN] Could not auto-enable API: {result.stderr.strip()}")
        print("       Enable manually: https://console.cloud.google.com/apis/library/youtube.googleapis.com"
              f"?project={project_id}")
        input("       Press Enter once enabled...")
    else:
        print("      [OK] YouTube Data API v3 enabled")

    # ── Steps 4+5: Playwright — consent screen + credentials ─────────────
    print(f"\n[4/5] Configuring OAuth consent screen and credentials via browser...")
    credentials_path = _playwright_setup(project_id, channel_name, email)

    if credentials_path is None:
        print("\n[WARN] Playwright automation failed or was skipped.")
        print("       Complete manually:")
        print(f"       1. https://console.cloud.google.com/apis/credentials/consent?project={project_id}")
        print(f"          - User Type: External → Create")
        print(f"          - App name: yt-automator-{channel_name}")
        print(f"          - Support email: {email}")
        print(f"          - Test users: add {email}")
        print(f"       2. https://console.cloud.google.com/apis/credentials?project={project_id}")
        print(f"          - + Create Credentials → OAuth client ID → Desktop app → Create → Download JSON")
        credentials_path = Path(
            input("\n       Paste the path to the downloaded credentials JSON: ").strip()
        ).expanduser().resolve()

    # ── Step 5: Wire up channel ───────────────────────────────────────────
    print(f"\n[5/5] Wiring up channel '{channel_name}'...")
    setup_channel(
        repo_root=repo_root,
        channel_name=channel_name,
        email=email,
        credentials_src=credentials_path,
    )


def _playwright_setup(project_id: str, channel_name: str, email: str) -> Path | None:
    """Use Playwright to configure OAuth consent screen and download credentials JSON."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        return None

    download_dir = Path(tempfile.mkdtemp())

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=300)
            ctx = browser.new_context(accept_downloads=True)
            page = ctx.new_page()

            # ── Sign in ───────────────────────────────────────────────────
            print("      Opening browser — sign in to GCP with your channel Gmail if prompted...")
            page.goto(
                f"https://console.cloud.google.com/apis/credentials/consent"
                f"?project={project_id}"
            )
            # Wait for the page to stabilise (handles sign-in redirect)
            page.wait_for_load_state("networkidle", timeout=60_000)
            time.sleep(2)

            # ── OAuth consent screen ──────────────────────────────────────
            try:
                # Select External if prompted
                ext = page.get_by_text("External", exact=True)
                if ext.is_visible(timeout=5_000):
                    ext.click()
                    page.get_by_role("button", name="Create").click()
                    page.wait_for_load_state("networkidle", timeout=30_000)

                # Fill app name
                page.get_by_label("App name").fill(f"yt-automator-{channel_name}")
                # Support email
                email_dropdown = page.locator("mat-select[formcontrolname='userSupportEmail']")
                if email_dropdown.is_visible(timeout=3_000):
                    email_dropdown.click()
                    page.get_by_role("option", name=email).first.click()
                # Developer email
                dev_email_field = page.locator("input[placeholder*='developer']").first
                if dev_email_field.is_visible(timeout=3_000):
                    dev_email_field.fill(email)

                page.get_by_role("button", name="Save and continue").click()
                page.wait_for_load_state("networkidle", timeout=30_000)
                # Skip Scopes
                page.get_by_role("button", name="Save and continue").click()
                page.wait_for_load_state("networkidle", timeout=30_000)
                # Add test user
                add_user_btn = page.get_by_role("button", name="Add users")
                if add_user_btn.is_visible(timeout=5_000):
                    add_user_btn.click()
                    page.locator("input[type='email'], input[placeholder*='email']").last.fill(email)
                    page.get_by_role("button", name="Add").click()
                    time.sleep(1)
                page.get_by_role("button", name="Save and continue").click()
                page.wait_for_load_state("networkidle", timeout=30_000)
                print("      [OK] OAuth consent screen configured")
            except PWTimeout:
                print("      [WARN] Could not fully automate consent screen — may already be configured")

            # ── Create credentials ────────────────────────────────────────
            page.goto(
                f"https://console.cloud.google.com/apis/credentials"
                f"?project={project_id}"
            )
            page.wait_for_load_state("networkidle", timeout=30_000)
            time.sleep(2)

            # Click + Create Credentials
            page.get_by_role("button", name=re.compile(r"Create credentials", re.I)).click()
            page.get_by_text("OAuth client ID").click()
            page.wait_for_load_state("networkidle", timeout=15_000)

            # Application type: Desktop app
            app_type = page.locator("mat-select[formcontrolname='applicationType']")
            app_type.click()
            page.get_by_role("option", name=re.compile(r"Desktop", re.I)).first.click()

            # Name
            name_field = page.get_by_label("Name")
            name_field.fill(f"yta-{channel_name}")

            # Create
            page.get_by_role("button", name="Create").click()
            page.wait_for_load_state("networkidle", timeout=20_000)
            time.sleep(1)

            # Download JSON from the confirmation dialog
            with page.expect_download(timeout=15_000) as dl_info:
                page.get_by_role("button", name=re.compile(r"download", re.I)).first.click()
            download = dl_info.value
            dest = download_dir / "credentials.json"
            download.save_as(str(dest))
            print("      [OK] Credentials downloaded")

            browser.close()
            return dest

    except Exception as exc:
        print(f"      [WARN] Playwright automation error: {exc}")
        try:
            browser.close()
        except Exception:
            pass
        return None
