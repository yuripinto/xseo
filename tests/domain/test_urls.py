from xseo.domain.urls import BaseUrl, NormalizedUrl, RawUrl


def test_raw_url_allows_relative_input():
    result = RawUrl.create("/about")

    assert result.ok
    assert result.value.value == "/about"


def test_base_url_requires_host():
    result = BaseUrl.create("https:///missing-host")

    assert not result.ok


def test_normalized_url_rejects_unsupported_scheme():
    result = NormalizedUrl.create("ftp://example.com/file")

    assert not result.ok
