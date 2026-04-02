from apps.social.cleaner import clean_text, is_quality_post


def test_removes_urls():
    result = clean_text("Check this out https://example.com/stock great stock")
    assert "http" not in result
    assert "great stock" in result


def test_removes_mentions():
    result = clean_text("@TraderJoe says $AAPL will moon today")
    assert "@TraderJoe" not in result
    assert "$AAPL" not in result
    assert "will moon today" in result


def test_collapses_whitespace():
    result = clean_text("too   many    spaces")
    assert "  " not in result
    assert result == "too many spaces"


def test_strips_leading_trailing():
    result = clean_text("  hello world  ")
    assert result == "hello world"


def test_quality_post_long_enough():
    assert is_quality_post("This stock looks promising today") is True


def test_quality_post_too_short():
    assert is_quality_post("buy") is False


def test_quality_post_empty():
    assert is_quality_post("") is False


def test_quality_post_only_whitespace():
    assert is_quality_post("   ") is False
