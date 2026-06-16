from __future__ import annotations

import logging
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from yt_automator.config import ConfigLoader
from yt_automator.models import PublishRecord
from yt_automator.optimizer.bandit_optimizer import BanditOptimizer
from yt_automator.pipeline.content_generator import ContentGenerator
from yt_automator.pipeline.media_sourcer import MediaSourcer
from yt_automator.pipeline.qa import QualityGate
from yt_automator.pipeline.run_logger import RunLogger
from yt_automator.pipeline.subtitles import SubtitleEngine
from yt_automator.pipeline.tts_engine import TTSEngine, run_async
from yt_automator.pipeline.video_renderer import VideoRenderer
from yt_automator.pipeline.youtube_client import YouTubeClient
from yt_automator.providers.nasa_provider import NasaProvider
from yt_automator.providers.pixabay_provider import PixabayProvider
from yt_automator.providers.wikimedia_provider import WikimediaProvider
from yt_automator.secrets import SecretManager
from yt_automator.utils.text import slugify
from yt_automator.utils.time_utils import generate_publish_schedule

_log = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_loader = ConfigLoader(repo_root)
        self.secret_manager = SecretManager(repo_root)
        self.app_settings = self.config_loader.load_app_settings()
        self.media_source_settings = self.config_loader.load_media_sources()

        optimizer_path = repo_root / "data" / "optimizer" / "bandit_state.json"
        self.optimizer = BanditOptimizer(optimizer_path)
        self.logger = RunLogger(repo_root / "data" / "runs")

    def list_channels(self) -> list[str]:
        return self.config_loader.list_channels()

    def get_channel_config(self, channel_name: str) -> dict:
        return self.config_loader.load_channel(channel_name)

    def run_batch(
        self,
        channels: list[str] | None,
        count: int,
        schedule: bool,
        dry_run: bool,
    ) -> None:
        targets = channels or self.list_channels()
        for channel in targets:
            self.run_once(
                channel_name=channel, count=count, schedule=schedule, dry_run=dry_run
            )

    def run_doctor(self, strict: bool = False) -> int:
        errors = 0
        warnings = 0
        _log.info("Running environment checks")

        for cmd in ("ffmpeg", "ffprobe"):
            if shutil.which(cmd):
                print(f"[OK] Found dependency: {cmd}")
            else:
                print(f"[FAIL] Missing dependency: {cmd}")
                errors += 1

        channels = self.list_channels()
        if not channels:
            print("[FAIL] No channel configs found in config/channels")
            errors += 1
        else:
            print(f"[OK] Found {len(channels)} channel configs")

        has_backend = bool(
            self.secret_manager.get("GEMINI_API_KEY")
            or self.secret_manager.get("OLLAMA_MODEL")
        )
        if has_backend:
            print("[OK] At least one generation backend configured")
        else:
            print("[WARN] No GEMINI_API_KEY or OLLAMA_MODEL set (fallback scripts used)")
            warnings += 1

        if self.secret_manager.get("PIXABAY_API_KEY"):
            print("[OK] PIXABAY_API_KEY is set")
        else:
            print("[WARN] PIXABAY_API_KEY not set (Wikimedia fallback will be used)")
            warnings += 1

        for channel in channels:
            cfg = self.get_channel_config(channel)
            creds_path, token_path = self._resolve_youtube_paths(cfg)
            if creds_path.exists():
                print(f"[OK] {channel}: credentials file found")
            else:
                print(f"[FAIL] {channel}: missing credentials at {creds_path}")
                errors += 1
            if not token_path.exists():
                print(f"[INFO] {channel}: token missing (created on first auth)")

            music_list = cfg["paths"]["music_files"]
            found = [
                n for n in music_list
                if (self.repo_root / "assets" / "music" / n).exists()
            ]
            if found:
                print(f"[OK] {channel}: found {len(found)} music file(s)")
            else:
                print(f"[WARN] {channel}: no music files found; silent fallback used")
                warnings += 1

        print(f"[INFO] Doctor summary: errors={errors} warnings={warnings}")

        if strict and (errors > 0 or warnings > 0):
            return 1
        return 1 if errors > 0 else 0

    def run_once(
        self,
        channel_name: str,
        count: int,
        schedule: bool,
        dry_run: bool,
    ) -> None:
        cfg = self.config_loader.load_channel(channel_name)
        history = self._load_topic_history(cfg)
        schedule_times: list[str] = []
        if schedule:
            schedule_times = generate_publish_schedule(
                cfg["youtube"]["daily_slots"],
                cfg["youtube"]["timezone"],
                count,
            )

        voices = self.app_settings["voices"]
        tts = TTSEngine(voices)
        subtitle_engine = SubtitleEngine(self.app_settings["subtitle_model"])
        qa_gate = QualityGate()

        gemini_key = self.secret_manager.get("GEMINI_API_KEY")
        ollama_model = self.secret_manager.get("OLLAMA_MODEL") or self.app_settings.get(
            "ollama_model"
        )
        ollama_base_url = self.app_settings.get("ollama_base_url", "http://localhost:11434")
        gemini_model = self.app_settings.get("gemini_model", "gemini-2.0-flash-lite")
        generator = ContentGenerator(
            gemini_key,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
            gemini_model=gemini_model,
        )

        media_sourcer = self._build_media_sourcer(channel_name)
        renderer = VideoRenderer()
        creds_path, token_path = self._resolve_youtube_paths(cfg)
        youtube_client = YouTubeClient(creds_path, token_path)

        for index in range(count):
            _log.info("[%s] Generating video %d/%d", channel_name, index + 1, count)

            strategy_key, strategy_data = self._pick_strategy(cfg)
            package = generator.generate(
                channel_config=cfg,
                strategy_key=strategy_key,
                strategy_data=strategy_data,
                history=history,
            )
            package.style_variant = strategy_key

            valid, issues = qa_gate.validate_content(package)
            if not valid:
                _log.warning("[%s] QA issues: %s", channel_name, issues)

            run_dir = self._new_run_dir(channel_name, package.topic)
            audio_path = run_dir / "voice.mp3"
            subtitle_path = run_dir / "subs.ass"
            video_path = run_dir / "final.mp4"

            voice = random.choice(voices)
            run_async(tts.synthesize(package.script, audio_path, voice=voice))
            segments = subtitle_engine.transcribe_segments(audio_path)
            subtitle_engine.write_ass(segments, subtitle_path)

            assets = media_sourcer.fetch_assets(
                package.video_query,
                run_dir / "assets",
                max_assets=cfg["pipeline"]["assets_per_video"],
            )

            music_path = self._resolve_music_file(cfg)
            render_result = renderer.render(
                assets=assets,
                voice_audio_path=audio_path,
                subtitle_path=subtitle_path,
                music_path=music_path,
                output_path=video_path,
            )

            publish_at = schedule_times[index] if schedule and index < len(schedule_times) else None
            upload_result = youtube_client.upload_short(
                video_path=render_result.video_path,
                title=package.title,
                description=package.description,
                tags=package.tags,
                category_id=cfg["youtube"]["category_id"],
                privacy_status=cfg["youtube"]["privacy_status"],
                publish_at=publish_at,
                dry_run=dry_run,
            )

            record = PublishRecord(
                channel=channel_name,
                package=package,
                render_result=render_result,
                upload_result=upload_result,
                scheduled_publish_at=publish_at,
                created_at=datetime.now(timezone.utc),
            )
            self.logger.log_publish_record(record)

            if upload_result.success:
                _log.info("[%s] Uploaded: %s", channel_name, upload_result.video_url)
                self._append_topic_history(cfg, package.topic)
                history.append(package.topic)
            else:
                _log.error("[%s] Upload failed: %s", channel_name, upload_result.error)

    def record_manual_reward(self, channel: str, arm: str, reward: float) -> None:
        self.optimizer.record_reward(channel, arm, reward)

    def _pick_strategy(self, cfg: dict) -> tuple[str, dict]:
        strategies = cfg["content_strategies"]
        arms = list(strategies.keys())
        epsilon = float(cfg["rl_profile"].get("epsilon", 0.2))
        chosen = self.optimizer.pick_arm(cfg["channel_name"], arms, epsilon)
        return chosen, strategies[chosen]

    def _build_media_sourcer(self, channel_name: str) -> MediaSourcer:
        providers = []
        pixabay_key = self.secret_manager.get("PIXABAY_API_KEY")
        for provider_cfg in self.media_source_settings.get("providers", []):
            if not provider_cfg.get("enabled", False):
                continue
            channels = provider_cfg.get("channels")
            if channels and channel_name not in channels:
                continue
            name = provider_cfg.get("name")
            if name == "pixabay":
                providers.append(PixabayProvider(pixabay_key))
            elif name == "wikimedia":
                providers.append(WikimediaProvider())
            elif name == "nasa":
                providers.append(NasaProvider(self.secret_manager.get("NASA_API_KEY")))
        if not providers:
            providers.append(WikimediaProvider())
        return MediaSourcer(providers)

    def _resolve_music_file(self, cfg: dict) -> Path:
        music_files = cfg["paths"]["music_files"]
        candidates = [
            self.repo_root / "assets" / "music" / name
            for name in music_files
            if (self.repo_root / "assets" / "music" / name).exists()
        ]
        if not candidates:
            fallback = self.repo_root / "assets" / "music" / "fallback_silent.mp3"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            if not fallback.exists():
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-f", "lavfi",
                        "-i", "anullsrc=r=44100:cl=mono",
                        "-t", "8", "-q:a", "9", "-acodec", "libmp3lame",
                        str(fallback),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            candidates.append(fallback)
        return random.choice(candidates)

    def _resolve_youtube_paths(self, cfg: dict) -> tuple[Path, Path]:
        creds_file = cfg["youtube"]["credentials_file"]
        token_file = cfg["youtube"]["token_file"]
        creds_path = self.repo_root / "secrets" / "youtube" / creds_file
        token_path = self.repo_root / "secrets" / "youtube" / token_file
        return creds_path, token_path

    def _load_topic_history(self, cfg: dict) -> list[str]:
        history_path = self.repo_root / cfg["paths"]["topic_history"]
        if not history_path.exists():
            return []
        try:
            return [
                line.strip()
                for line in history_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception as exc:
            _log.warning("Could not load topic history: %s", exc)
            return []

    def _append_topic_history(self, cfg: dict, topic: str) -> None:
        history_path = self.repo_root / cfg["paths"]["topic_history"]
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(topic + "\n")

    def _new_run_dir(self, channel: str, topic: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = slugify(topic)[:45]
        path = self.repo_root / "outputs" / channel / f"{timestamp}_{slug}"
        path.mkdir(parents=True, exist_ok=True)
        return path
