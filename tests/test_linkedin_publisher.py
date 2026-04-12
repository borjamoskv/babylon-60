from __future__ import annotations

from pathlib import Path

import httpx

from cortex.darknet.linkedin_publisher import (
    ArticlePost,
    LinkedInConfig,
    check_organization_post_permission,
    normalize_organization_urn,
    parse_markdown_article,
    resolve_organization_urn,
)


def test_normalize_organization_urn_supports_numeric_ids_and_brand_urns() -> None:
    assert normalize_organization_urn("12345") == "urn:li:organization:12345"
    assert (
        normalize_organization_urn("urn:li:organizationBrand:98765") == "urn:li:organization:98765"
    )


def test_config_prefers_organization_actor_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("LINKEDIN_REDIRECT_URI", "https://example.com/callback")
    monkeypatch.setenv("LINKEDIN_MEMBER_URN", "urn:li:person:member-1")
    monkeypatch.setenv("LINKEDIN_ORGANIZATION_URN", "12345")

    config = LinkedInConfig.from_env()

    assert config.member_urn == "urn:li:person:member-1"
    assert config.organization_urn == "urn:li:organization:12345"
    assert config.resolved_actor_urn() == "urn:li:organization:12345"
    assert config.resolved_actor_urn(prefer_organization=True) == "urn:li:organization:12345"


def test_article_post_hash_is_scoped_by_actor() -> None:
    post = ArticlePost(
        title="Title",
        description="Desc",
        article_url="https://example.com/articles/soft-post",
        commentary="Commentary",
        git_sha="abc123",
    )

    personal_hash = post.content_hash("urn:li:person:member-1")
    org_hash = post.content_hash("urn:li:organization:12345")

    assert personal_hash != org_hash


def test_parse_markdown_article_uses_frontmatter_linkedin_commentary(
    tmp_path: Path,
) -> None:
    md_file = tmp_path / "article.md"
    md_file.write_text(
        "---\n"
        'title: "Soft Article"\n'
        'description: "Desc"\n'
        'linkedin_commentary: "Custom LinkedIn teaser."\n'
        'linkedin_thumbnail_urn: "urn:li:image:abc123"\n'
        "---\n\n"
        "# Heading\n\n"
        "Body content that should not replace the custom teaser.\n",
        encoding="utf-8",
    )

    post = parse_markdown_article(md_file, "https://example.com/articles/soft-article")

    assert post.title == "Soft Article"
    assert post.description == "Desc"
    assert post.commentary == "Custom LinkedIn teaser."
    assert post.thumbnail_url == "urn:li:image:abc123"


def test_resolve_organization_urn_by_vanity(monkeypatch) -> None:
    def _fake_get(url: str, **kwargs):
        assert url == "https://api.linkedin.com/rest/organizations"
        assert kwargs["params"] == {"q": "vanityName", "vanityName": "acme-ai"}
        return httpx.Response(
            200,
            json={"elements": [{"id": 5515715, "localizedName": "Acme AI"}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    resolved = resolve_organization_urn(
        "token",
        "202510",
        organization_vanity="acme-ai",
    )

    assert resolved == "urn:li:organization:5515715"


def test_check_organization_post_permission_parses_approved(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_get(url: str, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        return httpx.Response(
            200,
            json={"status": {"com.linkedin.organization.Approved": {}}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = check_organization_post_permission(
        "token",
        "202510",
        "urn:li:person:member-1",
        "urn:li:organization:12345",
    )

    assert result == {"ok": True, "reasons": [], "error": None}
    assert "ORGANIC_SHARE_CREATE" in str(captured["url"])
    assert captured["headers"]["LinkedIn-Version"] == "202510"
