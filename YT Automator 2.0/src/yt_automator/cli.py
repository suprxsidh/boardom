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

    daemon_all_cmd = sub.add_parser("daemon-all", help="Run scheduler for all channels")
    daemon_all_cmd.add_argument("--dry-run", action="store_true")
    daemon_all_cmd.add_argument("--run-now", action="store_true")

    reward_cmd = sub.add_parser("record-reward", help="Record manual reward for a strategy arm")
    reward_cmd.add_argument("channel")
    reward_cmd.add_argument("arm")
    reward_cmd.add_argument("reward", type=float)

    doctor_cmd = sub.add_parser("doctor", help="Validate setup and credentials")
    doctor_cmd.add_argument("--strict", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    orchestrator = PipelineOrchestrator(get_repo_root())

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
        _run_daemon(orchestrator, args.channel, args.dry_run)

    elif args.command == "daemon-all":
        _run_daemon_all(orchestrator, args.dry_run, args.run_now)

    elif args.command == "record-reward":
        orchestrator.record_manual_reward(args.channel, args.arm, args.reward)
        print("[OK] Reward recorded")

    elif args.command == "doctor":
        raise SystemExit(orchestrator.run_doctor(strict=args.strict))


def _run_daemon(orchestrator: PipelineOrchestrator, channel: str, dry_run: bool) -> None:
    cfg = orchestrator.get_channel_config(channel)
    slots = cfg["youtube"]["daily_slots"]
    print(f"[INFO] Starting daemon for {channel}. Daily slots: {', '.join(slots)} IST")
    for slot in slots:
        schedule.every().day.at(slot).do(
            orchestrator.run_once,
            channel_name=channel, count=1, schedule=False, dry_run=dry_run,
        )
    orchestrator.run_once(channel_name=channel, count=1, schedule=False, dry_run=dry_run)
    while True:
        schedule.run_pending()
        time.sleep(1)


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
            schedule.every().day.at(slot).do(
                orchestrator.run_once,
                channel_name=channel, count=1, schedule=False, dry_run=dry_run,
            )
    if run_now:
        orchestrator.run_batch(channels=channels, count=1, schedule=False, dry_run=dry_run)
    while True:
        schedule.run_pending()
        time.sleep(1)
