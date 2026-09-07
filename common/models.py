"""
Data models
"""

import re
from dataclasses import dataclass, field
from enum import Enum

# Action vocabulary: internal token -> semantic explanation for the LLM.
# The explanation bridges the user's natural language prompt (e.g. "mark as read")
# to the action token the framework extracts and applies.
ACTION_DEFINITIONS = {
    "read": "mark the entry as read",
    "star": "bookmark the entry (star or favorite)",
    "save": "send the entry to configured third-party services",
}


@dataclass(frozen=True)
class Duration:
    """
    A positive duration as an amount plus a fixed time unit.

    Parses human-friendly strings like "5m" or "3w" and exposes the length in
    seconds. Per-field unit constraints (e.g. a scheduler interval may only use
    minutes/hours while an entry window may only use days/weeks) are enforced
    at parse time via `allowed_units`.

    Attributes:
        amount: Positive integer magnitude.
        unit:   Canonical time unit, one of Unit.
    """

    # Supported units and their length in seconds.
    Unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

    amount: int
    unit: str

    def __post_init__(self) -> None:
        if self.unit not in self.Unit:
            raise ValueError(f"Unsupported duration unit '{self.unit}'")
        if self.amount <= 0:
            raise ValueError(f"Duration amount must be positive, got {self.amount}")

    @classmethod
    def parse(
        cls,
        value: str | None,
        allowed_units: tuple[str, ...] | None = None,
    ) -> "Duration | None":
        """
        Parse a duration string such as "5m" or "3w" into a Duration.

        Args:
            value: Raw string; empty or None yields None (no constraint).
            allowed_units: Optional whitelist of units permitted for this field.
                Using any other unit raises ValueError, e.g. to forbid 'm'
                (minutes vs months) where it would be ambiguous.

        Returns:
            A Duration, or None when value was empty/None.

        Raises:
            ValueError: If the value is not a string, is malformed, uses a
                forbidden unit, or has a non-positive amount.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"Invalid duration {value!r}, expected e.g. '5m' or '3w'")
        value = value.strip()
        if not value:
            return None
        match = re.fullmatch(r"(\d+)([a-zA-Z]+)", value)
        if not match:
            raise ValueError(f"Invalid duration '{value}', expected e.g. '5m' or '3w'")
        amount, unit = int(match.group(1)), match.group(2)
        if unit not in cls.Unit:
            raise ValueError(
                f"Unsupported duration unit '{unit}' in '{value}', "
                f"supported: {', '.join(cls.Unit)}"
            )
        if allowed_units and unit not in allowed_units:
            raise ValueError(
                f"Unit '{unit}' in '{value}' is not allowed here, "
                f"use: {', '.join(allowed_units)}"
            )
        if amount <= 0:
            raise ValueError(f"Duration amount must be positive, got '{value}'")
        return cls(amount=amount, unit=unit)

    @property
    def seconds(self) -> int:
        """The duration expressed in whole seconds."""
        return self.amount * self.Unit[self.unit]

    def __str__(self) -> str:
        """Compact representation, e.g. '5m' or '3w'."""
        return f"{self.amount}{self.unit}"


@dataclass
class Agent:
    """
    Agent configuration with rule-based filtering

    Attributes:
        prompt: The prompt template for the agent
        template: The output template for formatting agent results
        allow_rules: List of rules in format "FieldName=RegEx". Entry must match at least one rule.
        deny_rules: List of rules in format "FieldName=RegEx". Entry must NOT match any rule.
        allow_actions: List of action names the agent may apply to the entry. Empty disables actions.
    """

    prompt: str
    template: str
    allow_rules: list[str] = field(default_factory=list)
    deny_rules: list[str] = field(default_factory=list)
    allow_actions: list[str] = field(default_factory=list)


class AgentResultStatus(Enum):
    """
    Status of agent processing operation
    """

    SUCCESS = "SUCCESS"
    FILTERED = "FILTERED"
    ERROR = "ERROR"


@dataclass
class AgentResult:
    """
    Result of an agent processing operation
    """

    status: AgentResultStatus
    content: str | None = None
    action: str | None = None
    error: Exception | None = None
    error_message: str | None = None

    @classmethod
    def success(cls, content: str, action: str | None = None) -> "AgentResult":
        """
        Create a successful agent result

        Args:
            content: The processed content
            action: Optional action applied to the entry

        Returns:
            AgentResult with SUCCESS status
        """
        return cls(status=AgentResultStatus.SUCCESS, content=content, action=action)

    @classmethod
    def filtered(cls) -> "AgentResult":
        """
        Create a filtered result (entry doesn't match criteria)

        Returns:
            AgentResult with FILTERED status
        """
        return cls(status=AgentResultStatus.FILTERED)

    @classmethod
    def from_error(cls, error: Exception, message: str | None = None) -> "AgentResult":
        """
        Create an error result

        Args:
            error: The exception that occurred
            message: Optional human-readable error message

        Returns:
            AgentResult with ERROR status
        """
        return cls(
            status=AgentResultStatus.ERROR,
            error=error,
            error_message=message or str(error),
        )

    @property
    def is_success(self) -> bool:
        """Check if processing was successful"""
        return self.status == AgentResultStatus.SUCCESS

    @property
    def is_filtered(self) -> bool:
        """Check if entry was filtered out"""
        return self.status == AgentResultStatus.FILTERED

    @property
    def is_error(self) -> bool:
        """Check if any error occurred"""
        return self.status == AgentResultStatus.ERROR

    def __bool__(self) -> bool:
        """
        Allow usage in boolean context
        Returns True only for successful results with content
        """
        return self.is_success and bool(self.content)

    def __str__(self) -> str:
        """String representation for logging"""
        if self.is_success:
            content_preview = (
                self.content[:50] + "..."
                if self.content and len(self.content) > 50
                else self.content
            )
            return f"AgentResult(SUCCESS, content='{content_preview}')"
        elif self.is_filtered:
            return "AgentResult(FILTERED)"
        else:
            return f"AgentResult(ERROR, message='{self.error_message}')"
