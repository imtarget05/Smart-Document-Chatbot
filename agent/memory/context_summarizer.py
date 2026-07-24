"""
Context summarizer — compresses long conversation history to stay within token limits.
When history exceeds threshold, summarizes older turns while keeping recent ones intact.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """You are a conversation summarizer. Condense the following conversation history into a concise summary (max 3 sentences) that preserves ALL important information needed for future responses.

Rules:
- Keep user preferences, facts, goals, project details, technical decisions.
- Remove greetings, pleasantries, repeated information.
- Be specific — include names, numbers, dates if mentioned.
- Output ONLY the summary, no preamble.

Conversation to summarize:
{conversation_text}
"""


class ContextSummarizer:
    """
    Compresses conversation history when token count exceeds threshold.

    Strategy:
    - Keep last K turns intact (recent = important)
    - Summarize everything before that into a single short paragraph
    - Store the summary per session in memory
    """

    def __init__(
        self, llm_router=None, max_turns_before_summary: int = 8, max_tokens: int = 2000
    ):
        self._llm = llm_router
        self.max_turns_before_summary = max_turns_before_summary
        self.max_tokens = max_tokens
        # Per-session cached summaries: {session_id: "summary text"}
        self._summaries: Dict[str, str] = {}

    def estimate_tokens(self, history: List[Dict[str, str]]) -> int:
        """Rough token estimate: ~4 chars per token."""
        total_chars = sum(len(m.get("content", "")) + 50 for m in history)
        return total_chars // 4

    def needs_summary(self, history: List[Dict[str, str]]) -> bool:
        """Check if history exceeds token threshold."""
        return (
            self.estimate_tokens(history) > self.max_tokens
            or len(history) > self.max_turns_before_summary * 2
        )

    def get_summary(self, session_id: str) -> str:
        """Get cached summary for a session."""
        return self._summaries.get(session_id, "")

    async def compress(
        self, session_id: str, history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Compress conversation history:
        - Keep last max_turns_before_summary turns intact
        - Summarize everything before that
        - Return compressed history with summary prepended

        Returns:
            List of messages: [{"role": "system", "content": "summary..."}, ...recent turns]
        """
        if not self.needs_summary(history):
            return history

        n = self.max_turns_before_summary
        old_turns = history[:-n] if len(history) > n else []
        recent_turns = history[-n:] if len(history) > n else history

        if not old_turns:
            return history

        # Build conversation text for summarization
        lines = []
        for m in old_turns:
            role = m.get("role", "user").capitalize()
            content = m.get("content", "")
            lines.append(f"{role}: {content[:500]}")
        conversation_text = "\n".join(lines)

        # Generate summary
        summary = await self._generate_summary(conversation_text)

        # Cache summary
        if summary:
            self._summaries[session_id] = summary

        # Build compressed history
        compressed = [
            {"role": "system", "content": f"[Conversation Summary] {summary}"}
        ]
        compressed.extend(recent_turns)

        logger.info(
            "ContextSummarizer: compressed %d turns → summary + %d turns (saved ~%d tokens)",
            len(old_turns),
            len(recent_turns),
            len(conversation_text) // 4 - len(summary) // 4,
        )

        return compressed

    async def _generate_summary(self, conversation_text: str) -> str:
        """Call LLM to generate summary."""
        # First check if we already have a summary for this content
        if len(conversation_text) < 100:
            return conversation_text[:200]

        if not self._llm:
            # Simple truncation fallback
            return f"Previous conversation: {conversation_text[:200]}..."

        prompt = SUMMARIZE_PROMPT.format(conversation_text=conversation_text[:4000])
        try:
            from langchain_core.messages import HumanMessage

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content.strip()
            return summary[:500]
        except Exception as exc:
            logger.warning(
                "ContextSummarizer: LLM call failed (%s), using truncation", exc
            )
            return f"Previous conversation: {conversation_text[:200]}..."

    def clear_session(self, session_id: str):
        self._summaries.pop(session_id, None)
