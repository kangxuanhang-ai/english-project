"""P0 spike：Fetch URL guard 冒烟。"""
from ai.services.mcp_url_guard import normalize_fetch_url, validate_fetch_url


def main() -> None:
    glued = "https://en.wikipedia.org/wiki/Calgary_Flames把这个网页的所有重要的单词都给我罗列出来"
    assert normalize_fetch_url(glued) == "https://en.wikipedia.org/wiki/Calgary_Flames"
    validate_fetch_url("https://www.bbc.com/news")
    validate_fetch_url("https://example.com/")
    try:
        validate_fetch_url("http://127.0.0.1/")
        raise AssertionError("should reject loopback")
    except ValueError:
        pass
    try:
        validate_fetch_url("http://169.254.169.254/")
        raise AssertionError("should reject metadata")
    except ValueError:
        pass
    try:
        validate_fetch_url("https://evil.test/")
        raise AssertionError("should reject non-allowlist")
    except ValueError:
        pass
    print("OK")


if __name__ == "__main__":
    main()
