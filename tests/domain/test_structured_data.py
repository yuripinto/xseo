from xseo.domain.extraction.structured_data import has_invalid_structured_data

VALID = '{"@context": "https://schema.org", "@type": "Article", "headline": "Hi"}'


def test_valid_jsonld_is_not_flagged():
    assert has_invalid_structured_data([VALID]) is False


def test_malformed_json_is_invalid():
    assert has_invalid_structured_data(['{"@type": "Article",}']) is True


def test_missing_type_is_invalid():
    assert has_invalid_structured_data(['{"@context": "https://schema.org"}']) is True


def test_missing_context_is_invalid():
    assert has_invalid_structured_data(['{"@type": "Article"}']) is True


def test_empty_block_is_invalid():
    assert has_invalid_structured_data(["   "]) is True


def test_graph_form_with_context_and_types_is_valid():
    block = (
        '{"@context": "https://schema.org", "@graph": ['
        '{"@type": "Organization"}, {"@type": "WebSite"}]}'
    )
    assert has_invalid_structured_data([block]) is False


def test_one_bad_block_among_good_ones_is_invalid():
    assert has_invalid_structured_data([VALID, "not json"]) is True
