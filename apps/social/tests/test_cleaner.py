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


# --- Phase 6: Enhanced financial text preprocessing ---


def test_cashtag_preserved_as_ticker():
    result = clean_text("$AAPL is looking strong today for investors")
    assert "AAPL" in result
    assert "$" not in result


def test_cashtag_multiple_preserved():
    result = clean_text("$MSFT and $GOOG are both bullish picks right now")
    assert "MSFT" in result
    assert "GOOG" in result


def test_html_entities_decoded():
    result = clean_text("Stock &amp; bonds are up &gt; 5% today")
    assert "&amp;" not in result
    assert "&gt;" not in result
    assert "& bonds" in result or "and bonds" in result


def test_rocket_emoji_maps_to_bullish():
    result = clean_text("AAPL to the moon \U0001f680\U0001f680\U0001f680 great earnings")
    assert "bullish" in result.lower()


def test_bear_emoji_maps_to_bearish():
    result = clean_text("Market looking rough \U0001f43b big crash coming")
    assert "bearish" in result.lower()


def test_chart_up_emoji_maps_to_bullish():
    result = clean_text("Numbers going up \U0001f4c8 all green today")
    assert "bullish" in result.lower()


def test_chart_down_emoji_maps_to_bearish():
    result = clean_text("Numbers tanking \U0001f4c9 red everywhere today")
    assert "bearish" in result.lower()


def test_reduces_repeated_chars():
    result = clean_text("This stock is goooood and amazzzzing for us")
    assert "gooo" not in result
    assert "zzz" not in result


def test_reduces_repeated_punctuation():
    result = clean_text("BUY NOW!!!!!! This is amazing!!!!! get in quick")
    assert "!!!" not in result


def test_expands_financial_abbreviations():
    result = clean_text("PT is 200 and the DD looks solid for this stock")
    assert "price target" in result.lower()
    assert "due diligence" in result.lower()


def test_quality_post_rejects_low_alpha_ratio():
    assert is_quality_post("123 456 789 !!! ??? ... ###") is False


def test_quality_post_accepts_good_alpha_ratio():
    assert is_quality_post("This stock has great fundamentals today") is True


def test_quality_post_rejects_pure_link_post():
    assert is_quality_post("http://example.com/stock-pick") is False


def test_removes_urls_preserves_cashtags():
    result = clean_text("Check https://link.com for AAPL analysis $AAPL rocks")
    assert "http" not in result
    assert "AAPL" in result
