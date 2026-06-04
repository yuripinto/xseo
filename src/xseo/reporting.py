"""Report building and rendering for the headless CLI.

A crawl's results are first turned into a plain ``dict`` report (``build_report``)
that is the single source of truth, then rendered into one of several output
formats. Keeping the renderers pure and dict-driven means they are trivial to
unit test and reuse — the CLI, a future hosted backend, and ``xseo diff`` all
build on the same shapes.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime

# Ordered low -> high so severities can be compared and ranked.
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}

# SARIF only has note/warning/error; map our three severities onto them.
_SARIF_LEVEL = {"low": "note", "medium": "warning", "high": "error"}


def _value(obj):
    """Unwrap a value object (``.value``) to a plain string, preserving ``None``."""
    if obj is None:
        return None
    return getattr(obj, "value", obj)


def build_report(state, start_url: str) -> dict:
    """Turn a results read-state into the canonical report dict."""
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
            "start_url": start_url,
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


def render_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def render_sarif(report: dict) -> str:
    """Render a SARIF 2.1.0 log so findings show up in GitHub code scanning."""
    rule_ids = sorted({issue["type"] for issue in report["issues"]})
    rules = [
        {
            "id": rule_id,
            "name": _camel(rule_id),
            "shortDescription": {"text": rule_id.replace("_", " ")},
        }
        for rule_id in rule_ids
    ]
    results = [
        {
            "ruleId": issue["type"],
            "level": _SARIF_LEVEL.get(issue["severity"], "warning"),
            "message": {"text": issue["explanation"]},
            "locations": [
                {"physicalLocation": {"artifactLocation": {"uri": issue["url"] or ""}}}
            ],
        }
        for issue in report["issues"]
    ]
    log = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "xseo",
                        "informationUri": "https://github.com/yuripinto/xseo",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(log, indent=2, ensure_ascii=False)


def render_html(report: dict) -> str:
    """Render a self-contained, shareable HTML report (no external assets)."""
    crawl = report["crawl"]
    by_severity = report["summary"]["by_severity"]

    severity_chips = "".join(
        f'<span class="chip {sev}">{by_severity.get(sev, 0)} {sev}</span>'
        for sev in ("high", "medium", "low")
    )

    issue_rows = "".join(
        "<tr>"
        f'<td><span class="badge {html.escape(issue["severity"])}">'
        f"{html.escape(issue['severity'].upper())}</span></td>"
        f"<td><code>{html.escape(issue['type'])}</code></td>"
        f"<td>{html.escape(issue['explanation'] or '')}</td>"
        f'<td class="url">{_link(issue["url"])}</td>'
        "</tr>"
        for issue in _sorted_issues(report["issues"])
    )
    if not issue_rows:
        issue_rows = '<tr><td colspan="4" class="empty">No issues found 🎉</td></tr>'

    generated = html.escape(crawl["generated_at"])
    start_url = html.escape(crawl["start_url"])
    return _HTML_TEMPLATE.format(
        start_url=start_url,
        generated=generated,
        pages=crawl["pages_crawled"],
        issues=crawl["issues_found"],
        duplicates=crawl["duplicate_groups"],
        severity_chips=severity_chips,
        issue_rows=issue_rows,
    )


def diff_reports(base: dict, head: dict) -> dict:
    """Compare two reports and report which issues are new, fixed, or unchanged.

    Issues are identified by ``(type, url)`` so re-running a crawl after fixing
    a page surfaces the delta a regression gate or changelog cares about.
    """
    base_keys = {_issue_key(i) for i in base["issues"]}
    head_index = {_issue_key(i): i for i in head["issues"]}
    head_keys = set(head_index)

    new = [head_index[k] for k in head_keys - base_keys]
    fixed = [i for i in base["issues"] if _issue_key(i) not in head_keys]
    unchanged = sorted(head_keys & base_keys)

    new.sort(key=_issue_sort_key)
    fixed.sort(key=_issue_sort_key)

    return {
        "base": {"issues_found": base["crawl"]["issues_found"]},
        "head": {"issues_found": head["crawl"]["issues_found"]},
        "new_issues": new,
        "fixed_issues": fixed,
        "unchanged": len(unchanged),
    }


def _issue_key(issue: dict) -> tuple[str, str]:
    return (issue["type"], issue["url"] or "")


def _issue_sort_key(issue: dict):
    return (-SEVERITY_RANK.get(issue["severity"], 0), issue["type"], issue["url"] or "")


def _sorted_issues(issues: list[dict]) -> list[dict]:
    return sorted(issues, key=_issue_sort_key)


def _camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _link(url: str | None) -> str:
    if not url:
        return ""
    safe = html.escape(url)
    return f'<a href="{safe}">{safe}</a>'


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>xseo report — {start_url}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; margin: 0;
         color: #1a1a1a; background: #fafafa; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e6e6e6; background: #161616; }}
    header, .card, table {{ background: #1f1f1f !important; }}
    td, th {{ border-color: #333 !important; }}
  }}
  header {{ padding: 28px 32px; background: #fff; border-bottom: 1px solid #e5e5e5; }}
  h1 {{ margin: 0 0 4px; font-size: 20px; }}
  .muted {{ color: #888; font-size: 13px; }}
  main {{ max-width: 1000px; margin: 0 auto; padding: 24px 32px; }}
  .stats {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 16px 0 8px; }}
  .stat .n {{ font-size: 28px; font-weight: 700; }}
  .stat .l {{ color: #888; font-size: 12px; text-transform: uppercase;
             letter-spacing: .04em; }}
  .chips {{ margin: 12px 0 24px; }}
  .chip {{ display: inline-block; padding: 3px 10px; border-radius: 999px;
          font-size: 12px; font-weight: 600; margin-right: 8px; }}
  .chip.high, .badge.high {{ background: #fde2e1; color: #a4140c; }}
  .chip.medium, .badge.medium {{ background: #fdecc8; color: #8a5a00; }}
  .chip.low, .badge.low {{ background: #e3eefb; color: #1a4f96; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff;
          border-radius: 8px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid #eee;
           vertical-align: top; }}
  th {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
       color: #888; }}
  .badge {{ display: inline-block; padding: 1px 8px; border-radius: 4px;
           font-size: 11px; font-weight: 700; }}
  code {{ font-size: 12px; }}
  td.url {{ max-width: 320px; word-break: break-all; }}
  td.url a {{ color: #1a73e8; text-decoration: none; }}
  .empty {{ text-align: center; color: #888; padding: 24px; }}
  footer {{ max-width: 1000px; margin: 0 auto; padding: 16px 32px 40px;
           color: #aaa; font-size: 12px; }}
</style>
</head>
<body>
<header>
  <h1>SEO report</h1>
  <div class="muted">{start_url} · generated {generated}</div>
</header>
<main>
  <div class="stats">
    <div class="stat"><div class="n">{pages}</div><div class="l">pages</div></div>
    <div class="stat"><div class="n">{issues}</div><div class="l">issues</div></div>
    <div class="stat"><div class="n">{duplicates}</div>
      <div class="l">duplicate groups</div></div>
  </div>
  <div class="chips">{severity_chips}</div>
  <table>
    <thead><tr><th>Severity</th><th>Type</th><th>Detail</th><th>URL</th></tr></thead>
    <tbody>{issue_rows}</tbody>
  </table>
</main>
<footer>Generated by <a href="https://github.com/yuripinto/xseo">xseo</a> —
a local-first SEO crawler.</footer>
</body>
</html>
"""
