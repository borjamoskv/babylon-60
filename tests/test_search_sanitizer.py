# [C5-REAL] Exergy-Maximized
"""Tests for SearchSanitizer."""

from __future__ import annotations

from babylon60.utils.search_sanitizer import SearchSanitizer


def test_sanitize_images():
    # Images with alt text should be replaced by their alt text
    raw = "Here is an image ![My Image](https://example.com/pic.png) and another without alt ![ ](https://foo.com/bar.jpg)."
    expected = "Here is an image My Image and another without alt   and another without alt  ."
    # Since we replace "!\[(.*?)\]\((.*?)\)" with "\1", ![My Image](url) -> "My Image"
    # and ![ ](url) -> " "
    sanitized = SearchSanitizer.sanitize_markdown(raw)
    assert "My Image" in sanitized
    assert "https://example.com/pic.png" not in sanitized
    assert "https://foo.com/bar.jpg" not in sanitized


def test_sanitize_safe_links():
    # Safe http/https/mailto links should be preserved
    raw = "[Google](https://google.com) and [Email](mailto:test@example.com) are safe."
    sanitized = SearchSanitizer.sanitize_markdown(raw)
    assert sanitized == raw


def test_sanitize_unsafe_links():
    # Unsafe javascript:, data:, file:, vbscript: links should have their URLs removed, keeping only the anchor text
    raw = "Run this [Malicious Link](javascript:alert('hack')) or look at [Data](data:text/html;base64,abc) or [Local File](file:///etc/passwd)."
    expected = "Run this Malicious Link or look at Data or Local File."
    sanitized = SearchSanitizer.sanitize_markdown(raw)
    assert sanitized == expected
    assert "javascript:" not in sanitized
    assert "data:" not in sanitized
    assert "file:" not in sanitized


def test_sanitize_scripts_and_comments():
    # Inline scripts and HTML comments should be completely stripped
    raw = "Text before <script type='text/javascript'>console.log('injected');</script> and <!-- HTML Comment --> text after."
    expected = "Text before  and  text after."
    sanitized = SearchSanitizer.sanitize_markdown(raw)
    assert sanitized == expected
    assert "<script" not in sanitized
    assert "HTML Comment" not in sanitized


def test_sanitize_empty_and_null():
    assert SearchSanitizer.sanitize_markdown("") == ""
    assert SearchSanitizer.sanitize_markdown(None) == ""  # type: ignore[arg-type]
