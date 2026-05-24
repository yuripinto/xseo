from xseo.domain.frontier import UrlNormalizer


def test_normalizer_lowercases_scheme_and_host_and_removes_fragment():
    result = UrlNormalizer().normalize("HTTPS://Example.COM/About#section")

    assert result.ok
    assert result.value.value == "https://example.com/About"


def test_normalizer_preserves_query_and_trailing_slash_distinctions():
    normalizer = UrlNormalizer()

    without_slash = normalizer.normalize("https://example.com/path?a=1").value
    with_slash = normalizer.normalize("https://example.com/path/?a=1").value
    other_query = normalizer.normalize("https://example.com/path?a=2").value

    assert without_slash.value != with_slash.value
    assert without_slash.value != other_query.value


def test_normalizer_resolves_relative_urls():
    result = UrlNormalizer().normalize_discovered("../next", "https://example.com/a/b/page")

    assert result.ok
    assert result.value.value == "https://example.com/a/next"


def test_normalizer_removes_default_ports():
    assert UrlNormalizer().normalize("http://example.com:80/").value.value == "http://example.com/"
    assert UrlNormalizer().normalize("https://example.com:443/").value.value == "https://example.com/"


def test_normalizer_rejects_unsupported_scheme():
    result = UrlNormalizer().normalize("ftp://example.com/file")

    assert not result.ok
