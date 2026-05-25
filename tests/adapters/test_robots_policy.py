from xseo.adapters.http.robots import AllowAllRobotsPolicy, RobotsTxtPolicy
from xseo.domain.urls import NormalizedUrl

ROBOTS = """
User-agent: *
Disallow: /private/
Disallow: /admin
"""


def _url(value):
    return NormalizedUrl.create(value).value


def test_disallowed_path_is_blocked():
    policy = RobotsTxtPolicy(lambda _: ROBOTS, user_agent="xseo")

    assert not policy.is_allowed(_url("https://example.com/private/page"))
    assert not policy.is_allowed(_url("https://example.com/admin"))


def test_allowed_path_is_permitted():
    policy = RobotsTxtPolicy(lambda _: ROBOTS, user_agent="xseo")

    assert policy.is_allowed(_url("https://example.com/"))
    assert policy.is_allowed(_url("https://example.com/blog/post"))


def test_missing_robots_fails_open():
    policy = RobotsTxtPolicy(lambda _: None, user_agent="xseo")

    assert policy.is_allowed(_url("https://example.com/anything"))


def test_robots_is_fetched_once_per_host():
    calls = []

    def fetch_text(robots_url):
        calls.append(robots_url)
        return ROBOTS

    policy = RobotsTxtPolicy(fetch_text, user_agent="xseo")
    policy.is_allowed(_url("https://example.com/a"))
    policy.is_allowed(_url("https://example.com/b"))
    policy.is_allowed(_url("https://other.com/a"))

    assert calls == [
        "https://example.com/robots.txt",
        "https://other.com/robots.txt",
    ]


def test_allow_all_policy_permits_everything():
    policy = AllowAllRobotsPolicy()

    assert policy.is_allowed(_url("https://example.com/private/"))
