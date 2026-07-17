import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import LLMFactory

logger = logging.getLogger(__name__)

SUMMARIZE_TURNS_THRESHOLD = 16


class ContextSummarizer:
    """
    LLM-based context summarization for long-running conversations.

    When a session exceeds SUMMARIZE_TURNS_THRESHOLD, older turns are
    condensed into a short summary so the active context window stays
    within token limits while preserving essential information.
    """

    def __init__(self, llm_factory=LLMFactory):
        self._llm = llm_factory.get_reasoning_model(temperature=0.3)

    async def summarize(
        self,
        turns: List[Dict[str, Any]],
        existing_summary: Optional[str] = None,
    ) -> str:
        """
        Generate a concise summary of conversation turns.

        Parameters
        ----------
        turns : list of {"role": str, "content": str, ...}
            Conversation turns to summarize.
        existing_summary : str, optional
            A previous summary to incorporate (incremental update).

        Returns
        -------
        str
            Markdown summary (3-5 sentences).
        """
        if not turns:
            return existing_summary or ""

        text = self._format_turns(turns[:SUMMARIZE_TURNS_THRESHOLD])
        prompt = self._build_summary_prompt(text, existing_summary)
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as exc:
            logger.warning("Context summarization failed: %s", exc)
            return existing_summary or text[:500]

    async def summarize_session(
        self,
        turns: List[Dict[str, Any]],
        existing_summary: Optional[str] = None,
    ) -> str:
        """
        Full-session summarization with explicit user goals and key decisions.
        """
        if not turns:
            return existing_summary or ""

        text = self._format_turns(turns[-SUMMARIZE_TURNS_THRESHOLD:])
        instruction = (
            "Summarize the conversation above. Include:\n"
            "1. The user's main goal / topic\n"
            "2. Key questions and answers\n"
            "3. Important decisions or conclusions\n"
            "4. Any unresolved follow-ups\n\n"
            "Keep it concise (3-6 sentences)."
        )
        if existing_summary:
            instruction = (
                f"Existing summary:\n{existing_summary}\n\n"
                f"Continue with new turns and update the summary:\n{instruction}"
            )
        prompt = f"{instruction}\n\nConversation:\n{text}\n\nSummary:"
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as exc:
            logger.warning("Session summarization failed: %s", exc)
            return existing_summary or text[:500]

    @staticmethod
    def _format_turns(turns: List[Dict[str, Any]]) -> str:
        lines = []
        for t in turns:
            role = t.get("role", "unknown")
            content = t.get("content", "")
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _build_summary_prompt(
        text: str, existing_summary: Optional[str] = None
    ) -> str:
        if existing_summary:
            return (
                f"Previous summary:\n{existing_summary}\n\n"
                f"New conversation turns:\n{text}\n\n"
                f"Update the summary to include the new turns. Keep it to 3-5 sentences.\n\nUpdated summary:"
            )
        return (
            f"Summarize the following conversation in 3-5 sentences. "
            f"Capture the user's goal, key questions, and answers.\n\n"
            f"Conversation:\n{text}\n\nSummary:"
        )
