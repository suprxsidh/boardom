from __future__ import annotations

import logging
import random
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from yt_automator.config import ConfigLoader
from yt_automator.models import PublishRecord
from yt_automator.optimizer.bandit_optimizer import BanditOptimizer
from yt_automator.pipeline.content_generator import ContentGenerator
from yt_automator.pipeline.thumbnail_generator import ThumbnailGenerator
from yt_automator.pipeline.media_sourcer import MediaSourcer
from yt_automator.pipeline.qa import QualityGate
from yt_automator.pipeline.run_logger import RunLogger
from yt_automator.pipeline.subtitles import SubtitleEngine
from yt_automator.pipeline.tts_engine import TTSEngine, run_async
from yt_automator.pipeline.video_renderer import VideoRenderer
from yt_automator.pipeline.youtube_client import YouTubeClient
from yt_automator.providers.nasa_provider import NasaProvider
from yt_automator.providers.pexels_provider import PexelsProvider
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
        print("[INFO] Running environment checks")

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

        if self.secret_manager.get("PEXELS_API_KEY"):
            print("[OK] PEXELS_API_KEY is set (video backgrounds enabled)")
        else:
            print("[WARN] PEXELS_API_KEY not set (falling back to Pixabay/Wikimedia images)")
            warnings += 1

        if self.secret_manager.get("PIXABAY_API_KEY"):
            print("[OK] PIXABAY_API_KEY is set")
        else:
            print("[INFO] PIXABAY_API_KEY not set (Wikimedia fallback will be used)")
            warnings += 1

        music_files = list((self.repo_root / "assets" / "music").glob("*.mp3"))
        if music_files:
            print(f"[OK] Found {len(music_files)} shared music file(s)")
        else:
            print("[WARN] No music files found in assets/music/; silent fallback used")
            warnings += 1

        for channel in channels:
            ch_dir = self.config_loader.channel_dir(channel)
            creds_path = ch_dir / "credentials.json"
            token_path = ch_dir / "token.json"
            if creds_path.exists():
                print(f"[OK] {channel}: credentials.json found")
            else:
                print(f"[FAIL] {channel}: missing credentials at {creds_path}")
                errors += 1
            if not token_path.exists():
                print(f"[INFO] {channel}: token.json missing (created on first auth)")

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
        ch_dir = self.config_loader.channel_dir(channel_name)
        history = self._load_topic_history(ch_dir)
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
        thumbnail_gen = ThumbnailGenerator()
        ch_dir = self.config_loader.channel_dir(channel_name)
        creds_path = ch_dir / "credentials.json"
        token_path = ch_dir / "token.json"
        youtube_client = YouTubeClient(creds_path, token_path)

        for index in range(count):
            _log.info("[%s] Generating video %d/%d", channel_name, index + 1, count)
            try:
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

                run_dir = self._new_run_dir(ch_dir, package.topic)
                audio_path = run_dir / "voice.mp3"
                subtitle_path = run_dir / "subs.ass"
                video_path = run_dir / "final.mp4"

                voice = random.choice(voices)

                # TTS and Pexels clip fetching are independent — run in parallel
                with ThreadPoolExecutor(max_workers=2) as pool:
                    tts_future = pool.submit(
                        run_async, tts.synthesize(package.script, audio_path, voice=voice)
                    )
                    base_clips = cfg["pipeline"]["assets_per_video"]
                    num_clips = random.randint(max(3, base_clips - 1), min(7, base_clips + 1))
                    assets_future = pool.submit(
                        media_sourcer.fetch_assets,
                        package.video_query,
                        run_dir / "assets",
                        num_clips,
                        package.scene_queries or None,
                    )
                    tts_future.result()
                    assets = assets_future.result()

                segments = subtitle_engine.transcribe_segments(audio_path)
                segments = subtitle_engine.correct_against_script(segments, package.script)
                subtitle_engine.write_ass(segments, subtitle_path)
                drawtext = subtitle_engine.build_drawtext_filter(segments)

                voice_duration = self._probe_duration(audio_path)
                music_path = self._resolve_music_file(min_duration=voice_duration)
                render_result = renderer.render(
                    assets=assets,
                    voice_audio_path=audio_path,
                    subtitle_path=subtitle_path,
                    music_path=music_path,
                    output_path=video_path,
                    drawtext_filter=drawtext,
                )

                thumbnail_path = thumbnail_gen.generate(
                    video_path=render_result.video_path,
                    title=package.title,
                    run_dir=run_dir,
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
                    thumbnail_path=thumbnail_path,
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
                    if not dry_run:
                        self._append_topic_history(ch_dir, package.topic)
                        self._cleanup_run_dir(run_dir)
                    history.append(package.topic)
                else:
                    _log.error("[%s] Upload failed: %s", channel_name, upload_result.error)
            except Exception as exc:
                _log.error(
                    "[%s] Video %d/%d failed, skipping: %s",
                    channel_name, index + 1, count, exc,
                    exc_info=True,
                )
                continue

    def run_analytics(self) -> None:
        from yt_automator.analytics.analytics_poller import AnalyticsPoller
        from yt_automator.analytics.reward import RewardCalculator
        poller = AnalyticsPoller(self.repo_root)
        poller.poll_all_channels()
        calculator = RewardCalculator(self.repo_root, self.optimizer)
        calculator.process_all_collected()

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
        pexels_key = self.secret_manager.get("PEXELS_API_KEY")
        for provider_cfg in self.media_source_settings.get("providers", []):
            if not provider_cfg.get("enabled", False):
                continue
            channels = provider_cfg.get("channels")
            if channels and channel_name.lower() not in [c.lower() for c in channels]:
                continue
            name = provider_cfg.get("name")
            if name == "pexels":
                providers.append(PexelsProvider(pexels_key))
            elif name == "pixabay":
                providers.append(PixabayProvider(pixabay_key))
            elif name == "wikimedia":
                providers.append(WikimediaProvider())
            elif name == "nasa":
                providers.append(NasaProvider(self.secret_manager.get("NASA_API_KEY")))
        if not providers:
            providers.append(WikimediaProvider())
        return MediaSourcer(providers)

    def _resolve_music_file(self, min_duration: float = 0.0) -> Path:
        music_dir = self.repo_root / "assets" / "music"
        candidates = [p for p in music_dir.glob("*.mp3") if p.is_file()]
        if not candidates:
            fallback = self.repo_root / "assets" / "music" / "fallback_silent.mp3"
            fallback.parent.mkdir(parents=True, exist_ok=True)
            if not fallback.exists():
                try:
                    import shutil as _shutil
                    _ffmpeg = _shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
                    subprocess.run(
                        [
                            _ffmpeg, "-y", "-f", "lavfi",
                            "-i", "anullsrc=r=44100:cl=mono",
                            "-t", "8", "-q:a", "9", "-acodec", "libmp3lame",
                            str(fallback),
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    candidates.append(fallback)
                except (FileNotFoundError, subprocess.CalledProcessError) as exc:
                    _log.warning(
                        "Could not generate silent fallback MP3 (%s); run 'brew install ffmpeg'",
                        exc,
                    )
            else:
                candidates.append(fallback)
        if not candidates:
            raise RuntimeError(
                "No music files found and could not create silent fallback. "
                "Place MP3 files in assets/music/ or install ffmpeg."
            )

        if min_duration > 0:
            durations = {p: self._probe_duration(p) for p in candidates}
            long_enough = [p for p, d in durations.items() if d >= min_duration]
            if long_enough:
                return random.choice(long_enough)
            # Fallback: pick the longest available track
            _log.warning(
                "No music track longer than %.1fs — using longest available", min_duration
            )
            return max(candidates, key=lambda p: durations[p])

        return random.choice(candidates)

    @staticmethod
    def _probe_duration(path: Path) -> float:
        import shutil as _shutil
        ffprobe = _shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
        try:
            out = subprocess.check_output(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            return float(out)
        except Exception:
            return 0.0

    def _cleanup_run_dir(self, run_dir: Path) -> None:
        try:
            shutil.rmtree(run_dir)
            _log.info("Cleaned up local files: %s", run_dir.name)
        except Exception as exc:
            _log.warning("Could not clean up run dir %s: %s", run_dir, exc)

    def _load_topic_history(self, ch_dir: Path) -> list[str]:
        history_path = ch_dir / "topics.txt"
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

    def _append_topic_history(self, ch_dir: Path, topic: str) -> None:
        history_path = ch_dir / "topics.txt"
        with history_path.open("a", encoding="utf-8") as handle:
            handle.write(topic + "\n")

    def _new_run_dir(self, ch_dir: Path, topic: str) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = slugify(topic)[:45]
        path = ch_dir / "outputs" / f"{timestamp}_{slug}"
        path.mkdir(parents=True, exist_ok=True)
        return path
