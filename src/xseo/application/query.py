"""Deterministic query helpers for application read models."""

from __future__ import annotations

from dataclasses import replace

from xseo.application.commands import QueryOptions
from xseo.application.results import ApplicationResult


def validate_query_options(options, allowed_sort_fields):
    if options is None:
        return ApplicationResult.ok(QueryOptions())
    if options.sort_direction not in {"asc", "desc"}:
        return ApplicationResult.fail(
            "Sort direction must be asc or desc", "query.invalid_sort_direction"
        )
    if options.sort_field is not None and options.sort_field not in allowed_sort_fields:
        return ApplicationResult.fail(
            "Sort field is not supported", "query.invalid_sort_field"
        )
    if options.page_size is not None and options.page_size <= 0:
        return ApplicationResult.fail(
            "Page size must be positive", "query.invalid_page_size"
        )
    if options.offset < 0:
        return ApplicationResult.fail(
            "Offset must be non-negative", "query.invalid_offset"
        )
    return ApplicationResult.ok(options)


def apply_query_options(rows, options=None, allowed_sort_fields=()):
    options = options or QueryOptions()
    validation = validate_query_options(options, allowed_sort_fields)
    if not validation.success:
        return validation

    result = tuple(_filter_rows(rows, options.filters or {}))
    if options.sort_field:
        reverse = options.sort_direction == "desc"
        result = tuple(
            sorted(
                result,
                key=lambda row: (
                    _sort_value(getattr(row, options.sort_field)),
                    _stable_row_key(row),
                ),
                reverse=reverse,
            )
        )
    if options.offset:
        result = result[options.offset :]
    if options.page_size is not None:
        result = result[: options.page_size]
    return ApplicationResult.ok(result)


def with_options(query, options):
    return replace(query, options=options)


def _filter_rows(rows, filters):
    for row in rows:
        if all(getattr(row, name, None) == value for name, value in filters.items()):
            yield row


def _sort_value(value):
    value = getattr(value, "value", value)
    if value is None:
        return (0, "")
    return (1, str(value))


def _stable_row_key(row):
    for name in ("page_id", "issue_id", "duplicate_group_id", "url", "affected_url"):
        value = getattr(row, name, None)
        if value is not None:
            return str(getattr(value, "value", value))
    return repr(row)
