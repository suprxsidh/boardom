from __future__ import annotations

import argparse
import time

import schedule

from yt_automator.pipeline.orchestrator import PipelineOrchestrator
from yt_automator.utils.paths import get_repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube Automator v2")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-channels", help="List available channels")

    run_cmd = sub.add_parser("run", help="Generate and upload videos now")
    run_cmd.add_argument("channel", help="Channel slug from config/channels")
    run_cmd.add_argument("--count", type=int, default=1)
    run_cmd.add_argument("--schedule-publish", action="store_true")
    run_cmd.add_argument("--dry-run", action="store_true")

    run_all_cmd = sub.add_parser("run-all", help="Run all channels")
    run_all_cmd.add_argument("--count", type=int, default=1)
    run_all_cmd.add_argument("--schedule-publish", action="store_true")
    run_all_cmd.add_argument("--dry-run", action="store_true")

    daemon_cmd = sub.add_parser("daemon", help="Run scheduler for one channel")
    daemon_cmd.add_argument("channel")
    daemon_cmd.add_argument("--dry-run", action="store_true")
    daemon_cmd.add_argument("--run-now", action="store_true",
                            help="Run once immediately before starting the scheduler loop")

    daemon_all_cmd = sub.add_parser("daemon-all", help="Run scheduler for all channels")
    daemon_all_cmd.add_argument("--dry-run", action="store_true")
    daemon_all_cmd.add_argument("--run-now", action="store_true")

    reward_cmd = sub.add_parser("record-reward", help="Record manual reward for a strategy arm")
    reward_cmd.add_argument("channel")
    reward_cmd.add_argument("arm")
    reward_cmd.add_argument("reward", type=float)

    doctor_cmd = sub.add_parser("doctor", help="Validate setup and credentials")
    doctor_cmd.add_argument("--strict", action="store_true")

    provision_cmd = sub.add_parser(
        "provision-channel",
        help="Fully provision a new channel (gcloud + Playwright + OAuth). "
             "Only needs Gmail + YouTube channel to already exist.",
    )
    provision_cmd.add_argument("name", help="Channel slug (e.g. history, space)")
    provision_cmd.add_argument("email", help="Gmail that owns the YouTube channel")

    sub.add_parser(
        "analytics",
        help="Poll YouTube Analytics for completed uploads and update RL bandit weights",
    )

    setup_cmd = sub.add_parser(
        "setup-channel",
        help="Wire up a new channel from a downloaded GCP credentials JSON",
    )
    setup_cmd.add_argument("name", help="Channel slug (e.g. history, space, finance)")
    setup_cmd.add_argument("email", help="Gmail address that owns the YouTube channel")
    setup_cmd.add_argument(
        "credentials",
        help="Path to the client_secret_*.json downloaded from GCP",
    )
    setup_cmd.add_argument(
        "--template",
        help="Existing channel to copy config from (default: auto-detected)",
        default=None,
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        orchestrator = PipelineOrchestrator(get_repo_root())
    except Exception as exc:
        print(f"[FAIL] Could not initialize: {exc}")
        print("[INFO] Run 'yta doctor' to diagnose setup issues.")
        raise SystemExit(1)

    if args.command == "list-channels":
        for ch in orchestrator.list_channels():
            print(ch)

    elif args.command == "run":
        orchestrator.run_once(
            channel_name=args.channel,
            count=max(args.count, 1),
            schedule=args.schedule_publish,
            dry_run=args.dry_run,
        )

    elif args.command == "run-all":
        orchestrator.run_batch(
            channels=None,
            count=max(args.count, 1),
            schedule=args.schedule_publish,
            dry_run=args.dry_run,
        )

    elif args.command == "daemon":
        _run_daemon(orchestrator, args.channel, args.dry_run, run_now=args.run_now)

    elif args.command == "daemon-all":
        _run_daemon_all(orchestrator, args.dry_run, args.run_now)

    elif args.command == "analytics":
        orchestrator.run_analytics()
        print("[OK] Analytics collection complete")

    elif args.command == "record-reward":
        orchestrator.record_manual_reward(args.channel, args.arm, args.reward)
        print("[OK] Reward recorded")

    elif args.command == "doctor":
        raise SystemExit(orchestrator.run_doctor(strict=args.strict))

    elif args.command == "provision-channel":
        from yt_automator.pipeline.channel_provision import provision_channel
        provision_channel(
            repo_root=get_repo_root(),
            channel_name=args.name,
            email=args.email,
        )

    elif args.command == "setup-channel":
        from yt_automator.pipeline.channel_setup import setup_channel
        from pathlib import Path as _Path
        setup_channel(
            repo_root=get_repo_root(),
            channel_name=args.name,
            email=args.email,
            credentials_src=_Path(args.credentials).expanduser().resolve(),
            template=args.template,
        )


def _ist_slot_to_local(slot: str) -> str:
    """Convert 'HH:MM' in IST to 'HH:MM' in the machine's local timezone."""
    import pytz
    from datetime import datetime
    hour, minute = (int(p) for p in slot.split(":"))
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now()
    ist_dt = ist.localize(datetime(now.year, now.month, now.day, hour, minute))
    local_dt = ist_dt.astimezone()
    return f"{local_dt.hour:02d}:{local_dt.minute:02d}"


def _run_daemon(orchestrator: PipelineOrchestrator, channel: str, dry_run: bool, run_now: bool = False) -> None:
    cfg = orchestrator.get_channel_config(channel)
    slots = cfg["youtube"]["daily_slots"]
    print(f"[INFO] Starting daemon for {channel}. Daily slots (IST): {', '.join(slots)}")
    for slot in slots:
        local_slot = _ist_slot_to_local(slot)
        schedule.every().day.at(local_slot).do(
            orchestrator.run_once,
            channel_name=channel, count=1, schedule=False, dry_run=dry_run,
        )
    if run_now:
        orchestrator.run_once(channel_name=channel, count=1, schedule=False, dry_run=dry_run)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Daemon stopped.")
        raise SystemExit(0)


def _run_daemon_all(
    orchestrator: PipelineOrchestrator, dry_run: bool, run_now: bool
) -> None:
    channels = orchestrator.list_channels()
    if not channels:
        print("[FAIL] No channels found")
        return
    print(f"[INFO] Starting daemon for all channels ({len(channels)} total)")
    for channel in channels:
        cfg = orchestrator.get_channel_config(channel)
        slots = cfg["youtube"]["daily_slots"]
        print(f"[INFO] {channel}: {', '.join(slots)}")
        for slot in slots:
            local_slot = _ist_slot_to_local(slot)
            schedule.every().day.at(local_slot).do(
                orchestrator.run_once,
                channel_name=channel, count=1, schedule=False, dry_run=dry_run,
            )
    if run_now:
        orchestrator.run_batch(channels=channels, count=1, schedule=False, dry_run=dry_run)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Daemon stopped.")
        raise SystemExit(0)
