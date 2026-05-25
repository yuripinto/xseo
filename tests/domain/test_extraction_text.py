from xseo.domain.extraction import (
    content_hash_for_text,
    normalize_visible_text,
    word_count,
)


def test_visible_text_collapses_whitespace():
    assert normalize_visible_text("  Hello\n\n world\t ") == "Hello world"


def test_word_count_is_non_negative_for_empty_text():
    assert word_count("") == 0


def test_content_hash_is_stable_for_equivalent_visible_text():
    first = content_hash_for_text("Hello   World")
    second = content_hash_for_text(" hello world ")

    assert first == second
