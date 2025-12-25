"""
Data models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


@dataclass
class Agent:
    """
    Agent configuration with rule-based filtering
    
    Attributes:
        prompt: The prompt template for the agent
        template: The output template for formatting agent results
        allow_rules: List of rules in format "FieldName=RegEx". Entry must match at least one rule.
        deny_rules: List of rules in format "FieldName=RegEx". Entry must NOT match any rule.
    """
    prompt: str
    template: str
    allow_rules: List[str] = field(default_factory=list)
    deny_rules: List[str] = field(default_factory=list)


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
    content: Optional[str] = None
    error: Optional[Exception] = None
    error_message: Optional[str] = None
    
    @classmethod
    def success(cls, content: str) -> 'AgentResult':
        """
        Create a successful agent result
        
        Args:
            content: The processed content
            
        Returns:
            AgentResult with SUCCESS status
        """
        return cls(
            status=AgentResultStatus.SUCCESS,
            content=content
        )
    
    @classmethod
    def filtered(cls) -> 'AgentResult':
        """
        Create a filtered result (entry doesn't match criteria)
        
        Returns:
            AgentResult with FILTERED status
        """
        return cls(status=AgentResultStatus.FILTERED)
    
    @classmethod
    def error(
        cls,
        error: Exception,
        message: Optional[str] = None
    ) -> 'AgentResult':
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
            error_message=message or str(error)
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
            content_preview = self.content[:50] + "..." if self.content and len(self.content) > 50 else self.content
            return f"AgentResult(SUCCESS, content='{content_preview}')"
        elif self.is_filtered:
            return "AgentResult(FILTERED)"
        else:
            return f"AgentResult(ERROR, message='{self.error_message}')"

