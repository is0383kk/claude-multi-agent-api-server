"""
FastAPI request/response models for Claude Agent SDK API

Defines data structures for API requests and responses.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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

    prompt: str = Field(..., description="Prompt to send to the agent")
    allowed_tools: Optional[List[str]] = Field(
        None, description="List of tool names allowed to be used"
    )
    system_prompt: Optional[str] = Field(None, description="System prompt")
    permission_mode: Optional[PermissionMode] = Field(
        None, description="Permission mode"
    )
    model: Optional[str] = Field(None, description="Model to use (sonnet, opus, haiku)")
    cwd: Optional[str] = Field(None, description="Current working directory")
    max_turns: Optional[int] = Field(None, description="Maximum conversation turns")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    disallowed_tools: Optional[List[str]] = Field(
        None, description="List of tool names prohibited from use"
    )
    resume_session_id: Optional[str] = Field(
        None,
        description="Session ID to resume. If specified, resumes existing session with the same session ID",
    )


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

    type: str = Field(..., description="Message type")
    content: Any = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")


class StatusResponse(BaseModel):
    """Response model for /status/{session_id} endpoint

    Returns information including session detailed status, message history, results, etc.
    """

    session_id: str = Field(..., description="Session ID")
    status: SessionStatus = Field(..., description="Current status")
    messages: List[MessageInfo] = Field(
        default_factory=list, description="List of messages"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Final result upon completion"
    )
    error: Optional[str] = Field(None, description="Error message upon failure")
    duration_ms: Optional[int] = Field(
        None, description="Execution time (milliseconds)"
    )
    total_cost_usd: Optional[float] = Field(None, description="Total cost (USD)")
