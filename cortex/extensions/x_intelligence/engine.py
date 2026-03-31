import logging

from cortex.cli.common import get_engine
from cortex.extensions.x_intelligence.client import XIntelligenceClient
from cortex.extensions.x_intelligence.models import XSearchResponse, XUser

LOG = logging.getLogger("cortex.extensions.x_intelligence.engine")


class XIntelligenceEngine:
    """Sovereign X Intelligence Engine — orchestrates extraction and CORTEX persistence."""

    def __init__(self, proxy: str | None = None):
        self.client = XIntelligenceClient(proxy=proxy)

    async def search_and_persist(
        self, query: str, limit: int = 20, project: str = "x-intelligence"
    ) -> XSearchResponse:
        """Search X and store results as CORTEX Facts."""
        LOG.info("🔍 [X] Searching for '%s' (limit=%d)...", query, limit)
        response = await self.client.search(query, limit)

        engine = get_engine()

        for tweet in response.tweets:
            # Create a CORTEX Fact for each tweet
            fact_data = {
                "tweet_id": tweet.id_str,
                "text": tweet.full_text,
                "author": tweet.user.screen_name if tweet.user else "unknown",
                "created_at": str(tweet.timestamp),
                "metrics": {"likes": tweet.favorite_count, "retweets": tweet.retweet_count},
            }

            # Store with Forensic identity
            await engine.store(
                content=tweet.full_text,
                metadata=fact_data,
                project=project,
                confidence="observed",
                source=f"agent:x-intelligence:search:{query}",
            )

        LOG.info("✅ [X] Persisted %d tweets to Ledger.", len(response.tweets))
        return response

    async def get_user_and_persist(
        self, screen_name: str, project: str = "x-intelligence"
    ) -> XUser | None:
        """Fetch user info and store as CORTEX Fact."""
        user = await self.client.get_user_by_screen_name(screen_name)
        if not user:
            return None

        engine = get_engine()
        await engine.store(
            content=f"X User profile: @{user.screen_name} - {user.description}",
            metadata=user.dict(),
            project=project,
            confidence="observed",
            source=f"agent:x-intelligence:user:{screen_name}",
        )
        return user

    async def close(self):
        await self.client.close()
