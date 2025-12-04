"""
FastAPI request/response models for Claude Agent SDK API

Defines data structures for API requests and responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SessionStatus(str, Enum):
    """Enumeration representing session status

    - PENDING: Session created but not yet executed
    - RUNNING: Agent is currently executing
    - COMPLETED: Execution completed successfully
    - ERROR: Error occurred during execution
    - CANCELLED: Cancelled by user
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class PermissionMode(str, Enum):
    """Enumeration representing agent permission modes

    - DEFAULT: Default permission mode
    - ACCEPT_EDITS: Automatically approve edit operations
    - PLAN: Plan mode (no actual changes are made)
    - BYPASS_PERMISSIONS: Bypass permission checks
    """

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    BYPASS_PERMISSIONS = "bypassPermissions"


class ExecuteRequest(BaseModel):
    """Request model for /execute/ endpoint

    Defines all parameters required for Claude agent execution.
    If resume_session_id is specified, resumes an existing session,
    otherwise creates a new session.
    """

    prompt: str = Field(..., description="Prompt to send to the agent", min_length=1)
    allowed_tools: Optional[List[str]] = Field(
        None, description="List of tool names allowed to be used"
    )
    system_prompt: Optional[str] = Field(None, description="System prompt")
    permission_mode: Optional[PermissionMode] = Field(
        None, description="Permission mode"
    )
    model: Optional[str] = Field(
        None, description="Model to use (sonnet, opus, haiku, etc.)"
    )
    cwd: Optional[str] = Field(None, description="Current working directory path")
    max_turns: Optional[int] = Field(
        None, description="Maximum conversation turns", ge=1, le=100
    )
    env: Optional[Dict[str, str]] = Field(
        None, description="Environment variables as key-value pairs"
    )
    disallowed_tools: Optional[List[str]] = Field(
        None, description="List of tool names prohibited from use"
    )
    resume_session_id: Optional[str] = Field(
        None,
        description="Session ID to resume. If specified, resumes existing session with the same session ID",
    )

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is not empty or whitespace only"""
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validate system_prompt: convert empty/whitespace-only strings to None"""
        if v is None:
            return None
        stripped = v.strip()
        # Empty or whitespace-only strings are converted to None
        if not stripped:
            return None
        return stripped


class ExecuteResponse(BaseModel):
    """Response model for /execute/ endpoint

    Returns the result of agent execution request.
    """

    session_id: str = Field(..., description="Generated session ID")
    status: SessionStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Status message")


class CancelResponse(BaseModel):
    """Response model for /cancel/{session_id} endpoint

    Returns the result of session cancellation operation.
    """

    session_id: str = Field(..., description="Cancelled session ID")
    status: SessionStatus = Field(..., description="Updated status")
    message: str = Field(..., description="Status message")


class MessageInfo(BaseModel):
    """Information about messages

    Holds details of messages sent and received during interactions with Claude agent.
    """

    type: str = Field(
        ..., description="Message type (e.g., UserMessage, AssistantMessage)"
    )
    content: Any = Field(..., description="Message content (serialized message data)")
    timestamp: str = Field(..., description="Message timestamp in ISO 8601 format")

    class Config:
        """Pydantic model configuration"""

        # Allow arbitrary types for content field
        arbitrary_types_allowed = True
        # Use enum values for serialization
        use_enum_values = True


class StatusResponse(BaseModel):
    """Response model for /status/{session_id} endpoint

    Returns comprehensive information including session status, message history, results, etc.
    """

    session_id: str = Field(..., description="Unique session identifier")
    status: SessionStatus = Field(..., description="Current execution status")
    messages: List[MessageInfo] = Field(
        default_factory=list, description="Chronological list of conversation messages"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Final execution result with metadata (if completed)"
    )
    error: Optional[str] = Field(
        None, description="Error message and details (if failed)"
    )
    duration_ms: Optional[int] = Field(
        None, description="Total execution time in milliseconds", ge=0
    )
    total_cost_usd: Optional[float] = Field(
        None, description="Total cost in USD (if available)", ge=0
    )

    class Config:
        """Pydantic model configuration"""

        use_enum_values = True
        json_encoders: Dict[type, Any] = {
            # Custom encoder for datetime objects if needed in the future
        }
