from app.okf.canonical import canonical_bytes, content_sha, short_sha


def test_sha_is_deterministic():
    fm = {"type": "skill", "title": "X"}
    assert content_sha(fm, "body") == content_sha(fm, "body")


def test_sha_ignores_frontmatter_key_order():
    a = content_sha({"a": 1, "b": 2}, "body")
    b = content_sha({"b": 2, "a": 1}, "body")
    assert a == b


def test_sha_normalizes_newlines_and_trailing_ws():
    a = content_sha({"t": 1}, "line1\nline2")
    b = content_sha({"t": 1}, "line1  \r\nline2\r\n\n")
    assert a == b


def test_sha_changes_with_content():
    assert content_sha({"t": 1}, "a") != content_sha({"t": 1}, "b")


def test_short_sha():
    sha = content_sha({"t": 1}, "a")
    assert short_sha(sha) == sha[:7]
    assert len(content_sha({"t": 1}, "a")) == 64
