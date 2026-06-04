"""Headless command-line interface for xseo.

Runs a crawl to completion against the same engine and SQLite store the desktop
app uses, prints a human-readable summary, optionally writes a machine-readable
report, and returns a CI-friendly exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from xseo import reporting
from xseo.composition import build_services

# Ordered low -> high so a "--fail-on" threshold can compare severities.
_SEVERITY_RANK = reporting.SEVERITY_RANK


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "crawl":
        return _run_crawl(args)
    if args.command == "diff":
        return _run_diff(args)
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
        choices=("json", "csv", "html", "sarif"),
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

    diff = sub.add_parser(
        "diff",
        help="Compare two JSON reports and show which issues are new or fixed.",
    )
    diff.add_argument("base", help="Baseline report (xseo crawl --out base.json).")
    diff.add_argument("head", help="Newer report to compare against the baseline.")
    diff.add_argument(
        "--out",
        metavar="FILE",
        help="Write the diff as JSON to FILE ('-' writes to stdout).",
    )
    diff.add_argument(
        "--fail-on-new",
        choices=("none", "low", "medium", "high"),
        default="none",
        help="Exit non-zero if a new issue at or above this severity appears.",
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

    report = reporting.build_report(state, args.url)
    renderers = {
        "json": reporting.render_json,
        "html": reporting.render_html,
        "sarif": reporting.render_sarif,
    }
    text = renderers[args.format](report)
    if args.out == "-":
        sys.stdout.write(text + "\n")
    else:
        Path(args.out).write_text(text, encoding="utf-8")


def _build_report(state, args) -> dict:
    """Backward-compatible shim around :func:`reporting.build_report`."""
    return reporting.build_report(state, args.url)


def _run_diff(args: argparse.Namespace) -> int:
    try:
        base = json.loads(Path(args.base).read_text(encoding="utf-8"))
        head = json.loads(Path(args.head).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read report: {exc}", file=sys.stderr)
        return 1

    diff = reporting.diff_reports(base, head)
    pipe_mode = args.out == "-"
    summary_stream = sys.stderr if pipe_mode else sys.stdout

    new = diff["new_issues"]
    fixed = diff["fixed_issues"]
    print(
        f"\n{len(new)} new, {len(fixed)} fixed, {diff['unchanged']} unchanged "
        f"({diff['base']['issues_found']} → {diff['head']['issues_found']} issues)",
        file=summary_stream,
    )
    for issue in new:
        print(
            f"  + {issue['severity'].upper():<7} {issue['type']}", file=summary_stream
        )
    for issue in fixed:
        print(
            f"  - {issue['severity'].upper():<7} {issue['type']}", file=summary_stream
        )

    if args.out:
        text = reporting.render_json(diff)
        if pipe_mode:
            sys.stdout.write(text + "\n")
        else:
            Path(args.out).write_text(text, encoding="utf-8")

    return _exit_code(_DiffIssue.wrap(new), args.fail_on_new)


class _DiffIssue:
    """Adapt a diff issue dict to the ``.severity`` shape ``_exit_code`` expects."""

    def __init__(self, severity: str) -> None:
        self.severity = severity

    @staticmethod
    def wrap(issues: list[dict]) -> list[_DiffIssue]:
        return [_DiffIssue(issue["severity"]) for issue in issues]


def _exit_code(issues, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = _SEVERITY_RANK[fail_on]
    for issue in issues:
        if _SEVERITY_RANK.get(str(issue.severity), 0) >= threshold:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
