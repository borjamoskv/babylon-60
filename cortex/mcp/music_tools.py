from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("cortex.mcp.music")


def _load_music_runtime():
    """Load the music runtime only when a music tool is invoked."""
    try:
        from cortex.extensions.music_engine.orchestrator import (
            GRAMMYOrchestrator,
            TrackContext,
        )
    except ImportError as exc:
        missing = getattr(exc, "name", None) or "optional music dependency"
        logger.warning("Music MCP tools unavailable: %s", exc)
        raise RuntimeError(
            f"Music engine unavailable. Install optional audio dependencies (missing {missing})."
        ) from exc

    return GRAMMYOrchestrator, TrackContext


def register_music_tools(mcp: FastMCP) -> None:  # type: ignore[reportInvalidTypeForm]
    """Registers GRAMMY-Ω Music Engine tools."""

    @mcp.tool()
    async def music_create_album(title: str, concept: str) -> str:
        """
        Creates a new music album concept.

        Args:
            title: The title of the album.
            concept: The artistic concept or mood (e.g., 'Berlin Techno 2026').
        """
        try:
            GRAMMYOrchestrator, _ = _load_music_runtime()
        except RuntimeError as exc:
            return str(exc)

        orchestrator = GRAMMYOrchestrator()
        album = await orchestrator.create_album(title, concept)  # type: ignore[type-error]
        return f"Album '{title}' created with ID: {album.id}. Concept: {concept}"

    @mcp.tool()
    async def music_generate_track(
        album_id: str, track_title: str, adapter: str = "suno_v5"
    ) -> str:
        """
        Generates a new track for an album using the specified AI music adapter.

        Args:
            album_id: The ID of the album.
            track_title: The title of the track.
            adapter: suno_v5, udio_v4, or lyria_3.
        """
        # Note: In a real implementation, we would retrieve the orchestrator
        # state from a persistent store or engine session.
        try:
            GRAMMYOrchestrator, TrackContext = _load_music_runtime()
        except RuntimeError as exc:
            return f"Error generating track: {exc}"

        orchestrator = GRAMMYOrchestrator()

        # Mocking album context if not found in session for this stateless tool example
        # In actual CORTEX, this would be tied to a persistent project context.
        orchestrator.current_album = await orchestrator.create_album("Draft", "Concept")  # type: ignore[type-error]

        track = TrackContext(id=f"trk_{track_title.lower().replace(' ', '_')}", title=track_title)

        try:
            result = await orchestrator.run_pipeline(track, provider=adapter)  # type: ignore[reportCallIssue]
            return (
                f"Track '{track_title}' generated successfully!\n"
                f"GRI Score: {result.gri_score:.2f}\n"
                f"State: {result.state.value}\n"
                f"Stems: {list(result.stems.keys())}"
            )
        except Exception as e:
            logger.error("Failed to generate track: %s", e)
            return f"Error generating track: {str(e)}"

    @mcp.tool()
    async def music_evaluate_gri(track_id: str, audio_path: str) -> str:
        """
        Evaluate the Grammy Readiness Index (GRI) of a track.
        """
        try:
            GRAMMYOrchestrator, TrackContext = _load_music_runtime()
        except RuntimeError as exc:
            return f"Evaluation failed: {exc}"

        orchestrator = GRAMMYOrchestrator()
        track = TrackContext(id=track_id, title="Evaluation")
        # In a real scenario, we'd load the audio and stems here.

        try:
            evaluated_track = await orchestrator.evaluate_track_gri(track)
            return f"GRI Evaluation complete for {track_id}. Score: {evaluated_track.gri_score:.2f}"  # type: ignore[type-error]
        except Exception as e:
            return f"Evaluation failed: {str(e)}"
