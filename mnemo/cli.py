"""Mnemo CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mnemo.config import load_config, resolve_vault, save_config
from mnemo.paths import VaultPaths
from mnemo.pipeline.capture import capture
from mnemo.pipeline.activity import load_recent_activity
from mnemo.pipeline.feedback import apply_feedback, review_feedback
from mnemo.pipeline.merge import apply_merges, suggest_merges
from mnemo.pipeline.query import query
from mnemo.pipeline.queue import consume_queue, queue_status
from mnemo.pipeline.status import build_status
from mnemo.store.repository import load_materialized, materialize
from mnemo.sync.health import sync_health
from mnemo.sync.mirror import mirror_vault


def ensure_paths(vault: Path) -> VaultPaths:
    paths = VaultPaths(vault)
    paths.ensure()
    return paths


def auto_consume(paths: VaultPaths, device_id: str, enabled: bool = True) -> None:
    if not enabled:
        return
    pending = [item for item in paths.queue.glob("*.json") if item.is_file()]
    if pending:
        consume_queue(paths, device_id=device_id)


def load_or_materialize(paths: VaultPaths, device_id: str, consume: bool = True) -> dict:
    auto_consume(paths, device_id=device_id, enabled=consume)
    materialized = load_materialized(paths)
    if not materialized:
        materialized = materialize(paths).to_dict()
    return materialized


def cmd_init(args) -> None:
    config = load_config()
    vault = Path(args.path).expanduser().resolve() if args.path else resolve_vault()
    config["vault_dir"] = str(vault)
    if args.device_id:
        config["device_id"] = args.device_id
    if args.mirror_dir is not None:
        config.setdefault("sync", {})["mirror_dir"] = str(Path(args.mirror_dir).expanduser())
    save_config(config)
    paths = ensure_paths(vault)
    materialize(paths)
    print(json.dumps({"status": "ok", "vault_dir": str(vault), "device_id": config["device_id"]}))


def cmd_capture(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    payload = json.load(sys.stdin)
    result = capture(paths, device_id=config["device_id"], payload=payload)
    print(json.dumps(result, indent=2))


def cmd_query(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    materialized = load_or_materialize(paths, device_id=config["device_id"], consume=not args.no_queue)
    print(json.dumps(query(materialized, args.question), indent=2))


def cmd_status(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    materialized = load_or_materialize(paths, device_id=config["device_id"], consume=not args.no_queue)
    result = build_status(materialized, str(paths.root), config.get("sync", {}), recent_activity=load_recent_activity(paths))
    result["queue"] = queue_status(paths)
    result["duplicates"] = materialized.get("duplicates", [])
    print(json.dumps(result, indent=2))


def cmd_rebuild(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    auto_consume(paths, device_id=config["device_id"], enabled=not args.no_queue)
    state = materialize(paths)
    print(json.dumps({
        "status": "ok",
        "entities": len(state.entities),
        "relations": len(state.relations),
        "sessions": len(state.sessions),
        "duplicates": len(state.duplicates),
    }, indent=2))


def cmd_auto(args) -> None:
    paths = ensure_paths(resolve_vault(args.vault))
    flag = paths.queue / ".auto-capture-enabled"
    if args.mode == "on":
        flag.write_text("enabled\n", encoding="utf-8")
        result = "enabled"
    elif args.mode == "off":
        if flag.exists():
            flag.unlink()
        result = "disabled"
    else:
        result = "enabled" if flag.exists() else "disabled"
    print(json.dumps({"status": "ok", "auto_capture": result}))


def cmd_sync_status(args) -> None:
    config = load_config()
    sync_config = config.get("sync", {})
    mirror_dir = sync_config.get("mirror_dir", "")
    print(json.dumps({
        "status": "ok",
        "vault_dir": str(resolve_vault(args.vault)),
        "mirror_dir": mirror_dir,
        "mirror_exists": bool(mirror_dir and Path(mirror_dir).expanduser().exists()),
        "recommended": [
            "Use a cloud-synced folder as the vault root for near-real-time multi-device reuse.",
            "Or set sync.mirror_dir and run `mnemo sync mirror` on a schedule.",
            "Run `mnemo sync health` before two-way syncing if multiple devices were active offline.",
        ],
    }, indent=2))


def cmd_sync_health(args) -> None:
    config = load_config()
    vault = resolve_vault(args.vault)
    raw_target = args.target or config.get("sync", {}).get("mirror_dir", "")
    if not raw_target:
        raise SystemExit("sync target missing: pass --target or set sync.mirror_dir in config")
    print(json.dumps(sync_health(vault, Path(raw_target).expanduser().resolve()), indent=2))


def cmd_sync_mirror(args) -> None:
    config = load_config()
    vault = resolve_vault(args.vault)
    raw_target = args.target or config.get("sync", {}).get("mirror_dir", "")
    if not raw_target:
        raise SystemExit("sync target missing: pass --target or set sync.mirror_dir in config")
    target = Path(raw_target).expanduser()
    if args.direction == "push":
        result = mirror_vault(vault, target.resolve())
    elif args.direction == "pull":
        result = mirror_vault(target.resolve(), vault)
    else:
        health = sync_health(vault, target.resolve())
        if health["files"]["divergent"]:
            raise SystemExit("cannot run two-way sync while divergent files exist; inspect `mnemo sync health` first")
        pull = mirror_vault(target.resolve(), vault)
        push = mirror_vault(vault, target.resolve())
        result = {"status": "ok", "direction": "both", "pull": pull, "push": push}
    print(json.dumps(result, indent=2))


def cmd_queue_status(args) -> None:
    paths = ensure_paths(resolve_vault(args.vault))
    print(json.dumps({"status": "ok", **queue_status(paths)}, indent=2))


def cmd_queue_consume(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    print(json.dumps(consume_queue(paths, device_id=config["device_id"], limit=args.limit), indent=2))


def cmd_activity_recent(args) -> None:
    paths = ensure_paths(resolve_vault(args.vault))
    print(json.dumps({"status": "ok", **load_recent_activity(paths)}, indent=2))


def cmd_merge(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    if args.stdin:
        payload = json.load(sys.stdin)
        print(json.dumps(apply_merges(paths, device_id=config["device_id"], payload=payload), indent=2))
        return
    materialized = load_or_materialize(paths, device_id=config["device_id"], consume=not args.no_queue)
    print(json.dumps({
        "status": "ok",
        "candidates": suggest_merges(materialized),
        "message": "Pipe merge instructions to `mnemo merge --stdin` with {'merges': [{'canonical': 'A', 'aliases': ['B']}]}",
    }, indent=2))


def cmd_feedback(args) -> None:
    config = load_config()
    paths = ensure_paths(resolve_vault(args.vault))
    if args.stdin:
        payload = json.load(sys.stdin)
        print(json.dumps(apply_feedback(paths, device_id=config["device_id"], payload=payload), indent=2))
        return
    materialized = load_or_materialize(paths, device_id=config["device_id"], consume=not args.no_queue)
    print(json.dumps({
        "status": "ok",
        **review_feedback(materialized),
        "message": "Pipe feedback operations to `mnemo feedback --stdin` with {'operations': [...]}",
    }, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mnemo", description="Local-first memory for coding agents")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="Initialize Mnemo vault")
    p.add_argument("path", nargs="?", default=None)
    p.add_argument("--device-id", default=None)
    p.add_argument("--mirror-dir", default=None)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("capture", help="Capture session knowledge from stdin")
    p.add_argument("--stdin", action="store_true", required=True)
    p.add_argument("--vault", default=None)
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("query", help="Query local memory")
    p.add_argument("--question", required=True)
    p.add_argument("--vault", default=None)
    p.add_argument("--no-queue", action="store_true", help="Skip auto-consuming queued breadcrumbs")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("status", help="Show vault status")
    p.add_argument("--vault", default=None)
    p.add_argument("--no-queue", action="store_true", help="Skip auto-consuming queued breadcrumbs")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("rebuild", help="Rebuild materialized views from event log")
    p.add_argument("--vault", default=None)
    p.add_argument("--no-queue", action="store_true", help="Skip auto-consuming queued breadcrumbs")
    p.set_defaults(func=cmd_rebuild)

    p = sub.add_parser("auto", help="Toggle auto-capture hook")
    p.add_argument("mode", choices=["on", "off", "status"], nargs="?", default="status")
    p.add_argument("--vault", default=None)
    p.set_defaults(func=cmd_auto)

    p = sub.add_parser("queue", help="Queue helpers")
    queue_sub = p.add_subparsers(dest="queue_command", required=True)

    p_queue_status = queue_sub.add_parser("status", help="Show pending queued breadcrumbs")
    p_queue_status.add_argument("--vault", default=None)
    p_queue_status.set_defaults(func=cmd_queue_status)

    p_queue_consume = queue_sub.add_parser("consume", help="Consume queued breadcrumbs into memory events")
    p_queue_consume.add_argument("--vault", default=None)
    p_queue_consume.add_argument("--limit", type=int, default=None)
    p_queue_consume.set_defaults(func=cmd_queue_consume)

    p = sub.add_parser("activity", help="Recent Codex activity helpers")
    activity_sub = p.add_subparsers(dest="activity_command", required=True)

    p_activity_recent = activity_sub.add_parser("recent", help="Show recent Codex write/edit activity captured by plugin hooks")
    p_activity_recent.add_argument("--vault", default=None)
    p_activity_recent.set_defaults(func=cmd_activity_recent)

    p = sub.add_parser("merge", help="Suggest or apply merges")
    p.add_argument("--vault", default=None)
    p.add_argument("--stdin", action="store_true", help="Read merge instructions from stdin")
    p.add_argument("--no-queue", action="store_true", help="Skip auto-consuming queued breadcrumbs")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("feedback", help="Review or apply feedback operations")
    p.add_argument("--vault", default=None)
    p.add_argument("--stdin", action="store_true", help="Read feedback operations from stdin")
    p.add_argument("--no-queue", action="store_true", help="Skip auto-consuming queued breadcrumbs")
    p.set_defaults(func=cmd_feedback)

    p = sub.add_parser("sync", help="Sync helpers")
    sync_sub = p.add_subparsers(dest="sync_command", required=True)

    p_status = sync_sub.add_parser("status", help="Show sync configuration")
    p_status.add_argument("--vault", default=None)
    p_status.set_defaults(func=cmd_sync_status)

    p_health = sync_sub.add_parser("health", help="Compare local and mirror vault state")
    p_health.add_argument("--vault", default=None)
    p_health.add_argument("--target", default=None)
    p_health.set_defaults(func=cmd_sync_health)

    p_mirror = sync_sub.add_parser("mirror", help="Mirror the vault into a cloud-synced folder")
    p_mirror.add_argument("--vault", default=None)
    p_mirror.add_argument("--target", default=None)
    p_mirror.add_argument("--direction", choices=["push", "pull", "both"], default="push")
    p_mirror.set_defaults(func=cmd_sync_mirror)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
