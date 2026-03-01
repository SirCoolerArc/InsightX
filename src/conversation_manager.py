"""
conversation_manager.py — InsightX Analytics Engine
====================================================
Responsible for maintaining conversation state across multiple turns.
Enables follow-up queries, drill-downs, and context-aware responses.

The conversation state is a simple Python dict — no database, no vector
store. Sufficient for the depth of conversation expected in this system.

Usage:
    from src.conversation_manager import ConversationManager

    cm = ConversationManager()
    cm.add_turn(user_query, parsed_intent, analytics_result, insight_response)
    context = cm.get_context()          # pass to query_parser
    history = cm.get_history()          # pass to Frontend UI for display
    cm.reset()                          # clear all state
"""

from dataclasses import dataclass, field
from typing import Optional
import json


# ---------------------------------------------------------------------------
# TURN — represents a single exchange in the conversation
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    """A single conversation turn (user query + system response)."""
    turn_number: int
    user_query: str
    parsed_intent: dict
    analytics_result: dict
    insight_response: str

    @property
    def intent(self) -> str:
        return self.parsed_intent.get("intent", "")

    @property
    def metric(self) -> str:
        return self.parsed_intent.get("metric", "")

    @property
    def filters(self) -> dict:
        return self.parsed_intent.get("filters", {}) or {}

    @property
    def group_by(self) -> Optional[str]:
        return self.parsed_intent.get("group_by")


# ---------------------------------------------------------------------------
# CONVERSATION MANAGER
# ---------------------------------------------------------------------------

class ConversationManager:
    """
    Manages conversation state across multiple turns.

    Key responsibilities:
    - Store turn history for display in the chat UI
    - Maintain active filters that persist across follow-up queries
    - Provide context dict to query_parser for follow-up resolution
    - Detect follow-up patterns and flag them for the parser
    """

    # Phrases that indicate a follow-up rather than a fresh query
    FOLLOWUP_PHRASES = [
        "break that down", "drill down", "what about", "how about",
        "compare with", "now look at", "same for", "and for",
        "why is that", "why does", "what causes", "can you explain",
        "show me", "also", "additionally", "furthermore",
        "what about on weekends", "what about on weekdays",
        "by state", "by age", "by bank", "by device", "by network",
        "for p2p", "for p2m", "for recharge", "for bill payment",
    ]

    def __init__(self):
        self._history: list[Turn] = []
        self._active_filters: dict = {}
        self._last_metric: Optional[str] = None
        self._last_segment: Optional[str] = None
        self._last_group_by: Optional[str] = None
        self._turn_count: int = 0
        self._code_history: list[dict] = []  # tracks code + results for follow-ups

    # -----------------------------------------------------------------------
    # CORE METHODS
    # -----------------------------------------------------------------------

    def add_turn(
        self,
        user_query: str,
        parsed_intent: dict,
        analytics_result: dict,
        insight_response: str,
        code: str = "",
        result_summary: str = "",
    ) -> None:
        """
        Record a completed conversation turn.
        Updates the active state based on what was just discussed.
        """
        self._turn_count += 1

        turn = Turn(
            turn_number=self._turn_count,
            user_query=user_query,
            parsed_intent=parsed_intent,
            analytics_result=analytics_result,
            insight_response=insight_response,
        )
        self._history.append(turn)

        # Track code history for follow-up context
        if code:
            self._code_history.append({
                "query": user_query,
                "code": code,
                "result_summary": result_summary,
            })

        # Update active state from this turn
        self._update_state(turn)

    def get_context(self) -> dict:
        """
        Return the current conversation context dict.
        Includes code history for the code interpreter pipeline.
        """
        return {
            "active_filters": self._active_filters.copy(),
            "last_metric": self._last_metric,
            "last_segment": self._last_segment,
            "last_group_by": self._last_group_by,
            "turn_count": self._turn_count,
            "is_followup": self._is_followup_likely(),
            "history": self._code_history[-3:],  # last 3 code turns for context
        }

    def get_history(self) -> list[dict]:
        """
        Return the conversation history as a list of dicts for Frontend UI display.
        Each dict has 'role' ('user' or 'assistant') and 'content' (str).
        """
        messages = []
        for turn in self._history:
            messages.append({
                "role": "user",
                "content": turn.user_query,
            })
            messages.append({
                "role": "assistant",
                "content": turn.insight_response,
            })
        return messages

    def get_last_result(self) -> Optional[dict]:
        """Return the analytics result from the most recent turn."""
        if not self._history:
            return None
        return self._history[-1].analytics_result

    def get_turn_count(self) -> int:
        """Return the number of completed turns."""
        return self._turn_count

    def reset(self) -> None:
        """Clear all conversation state. Called when user starts a new session."""
        self._history = []
        self._active_filters = {}
        self._last_metric = None
        self._last_segment = None
        self._last_group_by = None
        self._turn_count = 0
        self._code_history = []

    # -----------------------------------------------------------------------
    # STATE MANAGEMENT
    # -----------------------------------------------------------------------

    def _update_state(self, turn: Turn) -> None:
        """
        Update active filters and memory based on the completed turn.

        Strategy:
        - Merge new filters into active state (new values override old)
        - Clear filters that conflict with a clearly new topic
        - Always update last_metric, last_segment, last_group_by
        """
        new_filters = {k: v for k, v in turn.filters.items() if v is not None}

        # If this looks like a fresh query (not a follow-up), reset filters
        if not self._is_followup_likely() and self._turn_count > 1:
            self._active_filters = new_filters
        else:
            # Merge: new filters take precedence over old
            self._active_filters.update(new_filters)

        # Update memory
        self._last_metric = turn.metric or self._last_metric
        self._last_group_by = turn.group_by or self._last_group_by

        # Track the most prominent segment from the result
        summary = turn.analytics_result.get("summary", {})
        if isinstance(summary, dict):
            if "highest" in summary:
                self._last_segment = summary["highest"].get("segment")
            elif "top_segment" in summary:
                self._last_segment = summary.get("top_segment")

    def _is_followup_likely(self) -> bool:
        """
        Check if the most recent user query looks like a follow-up.
        Used to decide whether to inherit or reset active filters.
        """
        if not self._history:
            return False
        last_query = self._history[-1].user_query.lower()
        return any(phrase in last_query for phrase in self.FOLLOWUP_PHRASES)

    # -----------------------------------------------------------------------
    # UTILITY
    # -----------------------------------------------------------------------

    def summarise_state(self) -> str:
        """
        Return a human-readable summary of current conversation state.
        Useful for debugging in notebooks.
        """
        lines = [
            f"Turn count     : {self._turn_count}",
            f"Active filters : {json.dumps(self._active_filters)}",
            f"Last metric    : {self._last_metric}",
            f"Last segment   : {self._last_segment}",
            f"Last group_by  : {self._last_group_by}",
            f"Is follow-up   : {self._is_followup_likely()}",
        ]
        return "\n".join(lines)

    def get_conversation_summary(self) -> str:
        """
        Return a brief summary of what has been discussed.
        Used to provide context in longer conversations.
        """
        if not self._history:
            return "No conversation history yet."

        topics = []
        for turn in self._history[-3:]:  # last 3 turns only
            topics.append(f"Turn {turn.turn_number}: {turn.user_query}")

        return "Recent conversation:\n" + "\n".join(topics)


# ---------------------------------------------------------------------------
# Quick self-test — run from project root: python -m src.conversation_manager
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cm = ConversationManager()

    # Simulate a multi-turn conversation
    mock_turns = [
        {
            "user_query": "Which transaction type has the highest failure rate?",
            "parsed_intent": {
                "intent": "comparative",
                "metric": "failure_rate",
                "filters": {},
                "group_by": "transaction_type",
                "assumptions": [],
            },
            "analytics_result": {
                "success": True,
                "summary": {
                    "highest": {"segment": "Recharge", "value": 5.09},
                    "lowest": {"segment": "Bill Payment", "value": 4.88},
                },
            },
            "insight_response": "Recharge transactions have the highest failure rate at 5.09%.",
        },
        {
            "user_query": "Break that down by state",
            "parsed_intent": {
                "intent": "segmentation",
                "metric": "failure_rate",
                "filters": {},
                "group_by": "sender_state",
                "assumptions": ["Inherited transaction_type context from previous turn"],
            },
            "analytics_result": {
                "success": True,
                "summary": {
                    "highest": {"segment": "Uttar Pradesh", "value": 5.22},
                    "lowest": {"segment": "Telangana", "value": 4.71},
                },
            },
            "insight_response": "Uttar Pradesh shows the highest failure rate at 5.22%.",
        },
    ]

    for t in mock_turns:
        cm.add_turn(
            t["user_query"],
            t["parsed_intent"],
            t["analytics_result"],
            t["insight_response"],
        )
        print(f"\nAfter turn {cm.get_turn_count()}:")
        print(cm.summarise_state())

    print("\n--- Conversation History (for Frontend UI) ---")
    for msg in cm.get_history():
        role = "You" if msg["role"] == "user" else "BRAIN-DS"
        print(f"{role}: {msg['content']}")

    print("\n--- Context for next query ---")
    print(json.dumps(cm.get_context(), indent=2))