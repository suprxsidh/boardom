from __future__ import annotations

import logging
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from yt_automator.models import UploadResult

_log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
UPLOAD_PARTS = "snippet,status"


class YouTubeClient:
    def __init__(self, credentials_path: Path, token_path: Path):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> bool:
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    _log.warning("Token refresh failed: %s", exc)
                    creds = None
            if not creds:
                if not self.credentials_path.exists():
                    _log.error("Missing credentials file: %s", self.credentials_path)
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            self.token_path.chmod(0o600)
        self.service = build("youtube", "v3", credentials=creds)
        return True

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str,
        privacy_status: str,
        publish_at: str | None,
        dry_run: bool,
        thumbnail_path: Path | None = None,
    ) -> UploadResult:
        if dry_run:
            return UploadResult(
                success=True,
                video_url="https://www.youtube.com/watch?v=DRYRUN",
                video_id="DRYRUN",
            )

        if self.service is None and not self.authenticate():
            return UploadResult(
                success=False, video_url=None, video_id=None,
                error="Authentication failed",
            )

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": "private" if publish_at else privacy_status,
                "madeForKids": False,
                "selfDeclaredMadeForKids": False,
                "embeddable": True,
                "publicStatsViewable": True,
            },
        }
        if publish_at:
            body["status"]["publishAt"] = publish_at

        media = MediaFileUpload(
            str(video_path), chunksize=2 * 1024 * 1024, resumable=True, mimetype="video/mp4"
        )
        request = self.service.videos().insert(
            part=UPLOAD_PARTS, body=body, media_body=media
        )

        for attempt in range(3):
            try:
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        _log.info("Upload progress: %d%%", int(status.progress() * 100))
                video_id = response.get("id")
                if not video_id:
                    return UploadResult(
                        success=False, video_url=None, video_id=None,
                        error="YouTube API returned success but no video ID",
                    )
                if thumbnail_path and thumbnail_path.exists():
                    try:
                        self.service.thumbnails().set(
                            videoId=video_id,
                            media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
                        ).execute()
                        _log.info("Thumbnail uploaded for video %s", video_id)
                    except Exception as exc:
                        _log.warning("Thumbnail upload failed (non-fatal): %s", exc)
                return UploadResult(
                    success=True,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    video_id=video_id,
                )
            except HttpError as exc:
                if exc.resp.status in {500, 502, 503, 504} and attempt < 2:
                    time.sleep(5)
                    continue
                return UploadResult(
                    success=False, video_url=None, video_id=None, error=str(exc)
                )
            except (OSError, ConnectionError, TimeoutError) as exc:
                if attempt < 2:
                    _log.warning("Upload connection error (attempt %d/3): %s", attempt + 1, exc)
                    time.sleep(3)
                    continue
                return UploadResult(
                    success=False, video_url=None, video_id=None, error=str(exc)
                )

        return UploadResult(
            success=False, video_url=None, video_id=None, error="All upload attempts exhausted"
        )
