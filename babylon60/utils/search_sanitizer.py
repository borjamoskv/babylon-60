# [C5-REAL] Exergy-Maximized
"""SearchSanitizer - Deterministic syntactic sanitization module.

Filters external search results and scraped content to eliminate indirect
prompt injections (e.g. malicious images, javascript: links) while preserving
valid citations.
"""

from __future__ import annotations

import re
import urllib.parse


class SearchSanitizer:
    """Helper class to sanitize Markdown and text output from scrapers/search engines."""

    # Matches <script>...</script> tags
    _SCRIPT_RE = re.compile(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.IGNORECASE)

    # Matches HTML comments <!-- ... -->
    _COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

    # Allowed safe URL schemes
    _SAFE_SCHEMES = {"http", "https", "mailto"}

    @classmethod
    def sanitize_markdown(cls, text: str) -> str:
        """Sanitizes Markdown content by stripping image embeds and rewriting unsafe links.

        Utilizes an O(N) bracket-balancing scanner to robustly handle nested brackets
        and parentheses, avoiding ReDoS vulnerabilities and matching errors.

        Args:
            text: Raw markdown content.

        Returns:
            Sanitized markdown content.
        """
        if not text:
            return ""

        # 1. Strip script tags
        text = cls._SCRIPT_RE.sub("", text)

        # 2. Strip HTML comments
        text = cls._COMMENT_RE.sub("", text)

        # 3. Balanced scanner to parse images and links
        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            is_image = False
            start_token = i

            if text[i] == "!" and i + 1 < n and text[i + 1] == "[":
                is_image = True
                i += 1  # Advance to '['
            elif text[i] == "[":
                pass
            else:
                result.append(text[i])
                i += 1
                continue

            # Bracket matching for anchor text [anchor]
            bracket_depth = 1
            j = i + 1
            while j < n and bracket_depth > 0:
                if text[j] == "[":
                    bracket_depth += 1
                elif text[j] == "]":
                    bracket_depth -= 1
                j += 1

            # Verify closing bracket and subsequent opening parenthesis
            if bracket_depth > 0 or j >= n or text[j] != "(":
                result.append(text[start_token])
                i = start_token + 1
                continue

            anchor_text = text[i + 1 : j - 1]

            # Parenthesis matching for URL (url)
            paren_depth = 1
            k = j + 1
            while k < n and paren_depth > 0:
                if text[k] == "(":
                    paren_depth += 1
                elif text[k] == ")":
                    paren_depth -= 1
                k += 1

            if paren_depth > 0:
                result.append(text[start_token])
                i = start_token + 1
                continue

            url = text[j + 1 : k - 1].strip()

            # Sanitization logic
            if is_image:
                # Strip image markup completely, keeping alt text if present
                if anchor_text.strip():
                    result.append(anchor_text)
            else:
                # Link verification
                try:
                    parsed = urllib.parse.urlparse(url)
                    scheme = parsed.scheme.lower() if parsed.scheme else ""

                    if not scheme:
                        if url.lower().startswith(("javascript:", "data:", "file:", "vbscript:")):
                            result.append(anchor_text)
                        else:
                            # Relative URL or internal path - keep intact
                            result.append(text[start_token:k])
                    elif scheme in cls._SAFE_SCHEMES:
                        result.append(text[start_token:k])
                    else:
                        result.append(anchor_text)
                except ValueError:
                    result.append(anchor_text)

            i = k

        return "".join(result)
