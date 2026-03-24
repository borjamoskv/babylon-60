from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class XUser(BaseModel):
    """X User account model."""

    rest_id: str
    id_str: str = ""
    name: str
    screen_name: str
    description: str = ""
    location: str = ""
    followers_count: int = 0
    friends_count: int = 0
    statuses_count: int = 0
    favourites_count: int = 0
    listed_count: int = 0
    created_at: str = ""
    profile_image_url_https: str = ""
    verified: bool = False
    is_blue_verified: bool = False
    raw_data: dict[str, Any] = Field(default_factory=dict)


class XTweet(BaseModel):
    """X Tweet (post) model."""

    rest_id: str
    id_str: str = ""
    full_text: str
    created_at: str
    user_id_str: str
    user: XUser | None = None
    retweet_count: int = 0
    favorite_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    lang: str = "en"
    is_translatable: bool = False
    views_count: int | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)

    @property
    def timestamp(self) -> datetime:
        # Example format: "Thu Oct 24 14:02:44 +0000 2024"
        try:
            return datetime.strptime(self.created_at, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return datetime.now()


class XSearchResponse(BaseModel):
    """Structured response for search operations."""

    query: str
    tweets: list[XTweet] = Field(default_factory=list)
    users: list[XUser] = Field(default_factory=list)
    cursor: str | None = None
    has_more: bool = False
