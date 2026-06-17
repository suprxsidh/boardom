from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_log = logging.getLogger(__name__)

ANALYTICS_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class AnalyticsPoller:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.channels_dir = repo_root / "channels"
        self._state_path = repo_root / "data" / "analytics" / "collected.json"
        self._state: dict[str, bool] = self._load_state()

    def poll_all_channels(self) -> None:
        pending = self._collect_pending_records()
        if not pending:
            _log.info("No analytics records pending collection")
            return

        channels_with_pending: dict[str, list[dict]] = {}
        for rec in pending:
            channels_with_pending.setdefault(rec["channel"], []).append(rec)

        for channel, records in channels_with_pending.items():
            self._poll_channel(channel, records)

    def _poll_channel(self, channel: str, records: list[dict]) -> None:
        creds_path = self.channels_dir / channel / "credentials.json"
        token_path = self.channels_dir / channel / "analytics_token.json"

        if not creds_path.exists():
            _log.warning("[%s] No credentials.json — skipping analytics", channel)
            return

        try:
            creds = self._get_credentials(creds_path, token_path)
        except Exception as exc:
            _log.warning("[%s] Analytics auth failed: %s", channel, exc)
            return

        try:
            analytics_service = build("youtubeAnalytics", "v2", credentials=creds)
        except Exception as exc:
            _log.warning("[%s] Could not build analytics service: %s", channel, exc)
            return

        analytics_dir = self.channels_dir / channel / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        for rec in records:
            video_id = rec["video_id"]
            try:
                response = analytics_service.reports().query(
                    ids="channel==MINE",
                    startDate="2020-01-01",
                    endDate=today_str,
                    metrics="averageViewDuration,averageViewPercentage,views,likes,comments",
                    dimensions="video",
                    filters=f"video=={video_id}",
                ).execute()

                out_path = analytics_dir / f"{video_id}.json"
                out_path.write_text(
                    json.dumps({"record": rec, "analytics": response}, indent=2),
                    encoding="utf-8",
                )
                self._state[video_id] = True
                self._save_state()
                _log.info("[%s] Collected analytics for %s", channel, video_id)

            except Exception as exc:
                _log.warning("[%s] Analytics fetch failed for %s: %s", channel, video_id, exc)

    def _collect_pending_records(self) -> list[dict]:
        runs_dir = self.repo_root / "data" / "runs"
        if not runs_dir.exists():
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        pending: list[dict] = []

        for jsonl_path in sorted(runs_dir.glob("*.jsonl")):
            try:
                for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    video_id = rec.get("video_id")
                    if not video_id or video_id == "DRYRUN":
                        continue
                    if not rec.get("upload_success"):
                        continue
                    if self._state.get(video_id):
                        continue

                    created_at_str = rec.get("created_at", "")
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        if created_at > cutoff:
                            continue
                    except (ValueError, TypeError):
                        continue

                    pending.append(rec)
            except Exception as exc:
                _log.warning("Could not read run log %s: %s", jsonl_path, exc)

        return pending

    def _get_credentials(self, creds_path: Path, token_path: Path) -> Credentials:
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), ANALYTICS_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), ANALYTICS_SCOPES
                )
                creds = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")
            token_path.chmod(0o600)
        return creds

    def _load_state(self) -> dict[str, bool]:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(self._state, indent=2, sort_keys=True), encoding="utf-8"
        )
