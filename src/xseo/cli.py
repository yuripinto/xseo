"""Headless command-line interface for xseo.

Runs a crawl to completion against the same engine and SQLite store the desktop
app uses, prints a human-readable summary, optionally writes a machine-readable
report, and returns a CI-friendly exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from xseo.composition import build_services

# Ordered low -> high so a "--fail-on" threshold can compare severities.
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "crawl":
        return _run_crawl(args)
    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xseo",
        description="Local-first SEO crawler — audit a site from your terminal.",
    )
    sub = parser.add_subparsers(dest="command")

    crawl = sub.add_parser("crawl", help="Crawl a site and report SEO issues.")
    crawl.add_argument("url", help="Start URL, e.g. https://example.com/")
    crawl.add_argument(
        "--limit", type=int, default=500, help="Max pages to crawl (default: 500)."
    )
    crawl.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests, in seconds (default: 0.5).",
    )
    crawl.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Per-request timeout, in seconds (default: 10).",
    )
    crawl.add_argument(
        "--no-robots", action="store_true", help="Ignore robots.txt (be careful)."
    )
    crawl.add_argument(
        "--all-hosts",
        action="store_true",
        help="Follow links to other hosts (default: same host only).",
    )
    crawl.add_argument(
        "--out",
        metavar="FILE",
        help="Write a report to FILE ('-' writes JSON to stdout).",
    )
    crawl.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Report format for --out (default: json).",
    )
    crawl.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        default="none",
        help="Exit non-zero if an issue at or above this severity is found.",
    )
    crawl.add_argument(
        "--db",
        metavar="PATH",
        help="SQLite database path (default: ~/.xseo/xseo.sqlite3).",
    )
    return parser


def _run_crawl(args: argparse.Namespace) -> int:
    pipe_mode = args.out == "-"
    diag = sys.stderr
    summary_stream = sys.stderr if pipe_mode else sys.stdout

    services = build_services(args.db) if args.db else build_services()
    controller = services.controller

    print(f"Crawling {args.url} …", file=diag, flush=True)
    start = controller.start_crawl(
        args.url,
        same_host_only=not args.all_hosts,
        page_limit=args.limit,
        timeout_seconds=args.timeout,
        request_delay_seconds=args.delay,
        respect_robots=not args.no_robots,
    )
    if not start.success:
        print(f"error: {start.message}", file=diag)
        return 1

    crawl_id = controller.state.selected_crawl_id
    handle = services.bg_execution.get(crawl_id)
    if handle is not None:
        _wait_for_completion(handle, controller, diag)
        if handle.error is not None:
            print(f"error: crawl failed: {handle.error}", file=diag)
            return 1

    state = controller.refresh_results(crawl_id)
    if state.last_error:
        print(f"error: {state.last_error}", file=diag)
        return 1

    _print_summary(state, summary_stream)

    if args.out:
        try:
            _write_report(services, state, args)
        except Exception as exc:  # noqa: BLE001 - surface any write/export failure
            print(f"error: could not write report: {exc}", file=diag)
            return 1
        if not pipe_mode:
            print(f"Report → {args.out}", file=diag)

    return _exit_code(state.issues, args.fail_on)


def _wait_for_completion(handle, controller, diag) -> None:
    """Block until the background crawl thread finishes, stopping it on Ctrl-C."""
    try:
        while not handle.done:
            handle.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\nstopping… (waiting for in-flight request)", file=diag, flush=True)
        controller.stop_crawl()
        while not handle.done:
            handle.join(timeout=0.5)


def _print_summary(state, stream) -> None:
    pages = len(state.pages)
    issues = state.issues
    print(f"\nCrawled {pages} pages, found {len(issues)} issues", file=stream)
    if not issues:
        return

    counts: dict[tuple[str, str], int] = {}
    for issue in issues:
        key = (str(issue.severity), str(issue.issue_type))
        counts[key] = counts.get(key, 0) + 1

    ordered = sorted(
        counts.items(),
        key=lambda item: (-_SEVERITY_RANK.get(item[0][0], 0), -item[1], item[0][1]),
    )
    print(file=stream)
    for (severity, issue_type), count in ordered:
        print(f"  {severity.upper():<7} {count:>4}  {issue_type}", file=stream)


def _write_report(services, state, args) -> None:
    if args.format == "csv":
        if args.out == "-":
            raise ValueError("CSV output requires a file path, not '-'")
        result = services.controller.export_issues(args.out)
        if not (result and result.success):
            message = services.controller.state.last_error or "CSV export failed"
            raise RuntimeError(message)
        return

    report = _build_report(state, args)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out == "-":
        sys.stdout.write(text + "\n")
    else:
        Path(args.out).write_text(text, encoding="utf-8")


def _build_report(state, args) -> dict:
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    issues = []
    for issue in state.issues:
        severity = str(issue.severity)
        issue_type = str(issue.issue_type)
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_type[issue_type] = by_type.get(issue_type, 0) + 1
        issues.append(
            {
                "severity": severity,
                "type": issue_type,
                "url": _value(issue.affected_url),
                "explanation": issue.explanation,
            }
        )

    pages = [
        {
            "url": _value(page.final_url) or _value(page.url),
            "status_code": page.status_code,
            "title": page.title,
            "word_count": page.word_count,
        }
        for page in state.pages
    ]
    duplicates = [
        {
            "page_count": group.page_count,
            "representative_url": _value(group.representative_url),
        }
        for group in state.duplicate_groups
    ]

    return {
        "crawl": {
            "start_url": args.url,
            "pages_crawled": len(state.pages),
            "issues_found": len(state.issues),
            "duplicate_groups": len(state.duplicate_groups),
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "summary": {"by_severity": by_severity, "by_type": by_type},
        "issues": issues,
        "pages": pages,
        "duplicate_groups": duplicates,
    }


def _exit_code(issues, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = _SEVERITY_RANK[fail_on]
    for issue in issues:
        if _SEVERITY_RANK.get(str(issue.severity), 0) >= threshold:
            return 1
    return 0


def _value(obj):
    """Unwrap a value object (``.value``) to a plain string, preserving ``None``."""
    if obj is None:
        return None
    return getattr(obj, "value", obj)


if __name__ == "__main__":
    sys.exit(main())
