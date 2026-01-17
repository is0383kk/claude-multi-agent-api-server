"""
FastAPI application for Claude Agent SDK

Provides a web service for asynchronous execution of Claude Agent SDK via HTTP endpoints.
"""

import os
from typing import Any, Dict, List, Union

from claude_agent_sdk import ClaudeAgentOptions
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CancelResponse,
    DeleteResponse,
    ExecuteRequest,
    ExecuteResponse,
    SessionStatus,
    StatusResponse,
)
from session_manager import SessionManager

# Create FastAPI application
app = FastAPI(
    title="Claude Agent SDK API",
    description="Claude Agent SDK execution API with session management",
    version="1.0.0",
)

# Add CORS middleware
# Note: Specify specific origins in production environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify actual origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global session manager
# Manages session state across the entire application
session_manager = SessionManager()


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint - Returns basic API information"""
    return {
        "message": "Claude Agent SDK API",
        "version": "1.0.0",
        "endpoints": {
            "execute": "POST /execute/ - Execute a new agent session",
            "status": "GET /status/{session_id} - Get session status",
            "cancel": "POST /cancel/{session_id} - Cancel a running session",
            "delete": "DELETE /sessions/{session_id} - Delete a specific session",
            "sessions": "GET /sessions/ - List all sessions",
            "cleanup": "DELETE /sessions/cleanup - Cleanup old sessions",
        },
    }


def _extract_permission_mode(permission_mode: Any) -> str:
    """
    Extract permission mode value from enum or string

    Args:
        permission_mode: Permission mode (enum or string)

    Returns:
        Permission mode as string
    """
    if hasattr(permission_mode, "value"):
        return permission_mode.value
    return str(permission_mode)


def _build_agent_options(request: ExecuteRequest) -> ClaudeAgentOptions:
    """
    Build ClaudeAgentOptions from ExecuteRequest

    Args:
        request: Execution request containing agent configuration

    Returns:
        ClaudeAgentOptions configured with request parameters
    """
    options_dict: Dict[str, Any] = {
        "cwd": request.cwd or os.getcwd(),
    }

    # Tool configurations
    if request.allowed_tools is not None:
        options_dict["allowed_tools"] = _ensure_list(request.allowed_tools)

    if request.disallowed_tools is not None:
        options_dict["disallowed_tools"] = _ensure_list(request.disallowed_tools)

    # Text configurations
    if request.system_prompt is not None:
        options_dict["system_prompt"] = request.system_prompt

    # Permission mode
    if request.permission_mode is not None:
        options_dict["permission_mode"] = _extract_permission_mode(
            request.permission_mode
        )

    # Model and limits
    if request.model is not None:
        options_dict["model"] = request.model

    if request.max_turns is not None:
        options_dict["max_turns"] = request.max_turns

    # Environment variables
    if request.env is not None:
        options_dict["env"] = request.env

    return ClaudeAgentOptions(**options_dict)


def _ensure_list(value: Union[str, List[str], Any]) -> List[str]:
    """
    Ensures the value is a list and converts single values to single-element lists

    Args:
        value: Value to convert to list (string, list, or other iterable object)

    Returns:
        List containing the value(s)
    """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return value
    else:
        # Try to convert iterable object to list
        try:
            return list(value)
        except (TypeError, ValueError):
            # If not iterable, wrap in list
            return [str(value)]


@app.post("/execute/", response_model=ExecuteResponse)
async def execute_agent(request: ExecuteRequest) -> ExecuteResponse:
    """
    Execute a new Claude agent session
    or
    Resume an existing session by specifying a session ID

    Args:
        request: Execution request containing prompt, options, and optional resume_session_id

    Returns:
        ExecuteResponse containing session_id and status
    """
    try:
        # Build ClaudeAgentOptions from request
        agent_options = _build_agent_options(request)

        # Create or resume session
        session = await session_manager.create_session(
            request.prompt, agent_options, request.resume_session_id
        )

        # Set message for new/resumed session
        message = (
            f"Session {session.session_id} resumed successfully"
            if request.resume_session_id
            else f"Session {session.session_id} started successfully"
        )

        return ExecuteResponse(
            session_id=session.session_id,
            status=session.status,
            message=message,
        )

    except ValueError as e:
        # Session resume or validation errors
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Unexpected errors
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        ) from e


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(
    session_id: str = Path(..., description="Session ID to get status for"),
) -> StatusResponse:
    """
    Get session status

    Args:
        session_id: Session ID to query

    Returns:
        StatusResponse containing session status and messages
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Extract cost information safely
    total_cost_usd = None
    if session.result and isinstance(session.result, dict):
        total_cost_usd = session.result.get("total_cost_usd")

    return StatusResponse(
        session_id=session.session_id,
        status=session.status,
        messages=session.messages,
        result=session.result,
        error=session.error,
        duration_ms=session.get_duration_ms(),
        total_cost_usd=total_cost_usd,
    )


@app.post("/cancel/{session_id}", response_model=CancelResponse)
async def cancel_session(
    session_id: str = Path(..., description="Session ID to cancel"),
) -> CancelResponse:
    """
    Cancel a running session

    Args:
        session_id: Session ID to cancel

    Returns:
        CancelResponse containing updated status
    """
    # Get session from session ID
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Check if session is in a cancellable state
    if session.status != SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} is not running (status: {session.status})",
        )

    # Attempt to cancel the session
    success = await session_manager.cancel_session(session_id)

    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel session {session_id}"
        )

    return CancelResponse(
        session_id=session_id,
        status=SessionStatus.CANCELLED,
        message=f"Session {session_id} cancelled successfully",
    )


@app.get("/sessions/")
async def list_sessions() -> List[Dict[str, Any]]:
    """
    List all sessions with detailed information

    Returns:
        List of session detailed information
    """
    return await session_manager.get_all_sessions()


@app.delete("/sessions/cleanup")
async def cleanup_sessions(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up old sessions

    Args:
        max_age_hours: Maximum age of sessions to keep (default: 24 hours)

    Returns:
        Dictionary with cleanup results
    """
    removed = await session_manager.cleanup_old_sessions(max_age_hours)
    return {"removed": removed, "message": f"Cleaned up {removed} old sessions"}


@app.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str = Path(..., description="Session ID to delete"),
) -> DeleteResponse:
    """
    Delete a specific session by session ID

    Deletes the specified session from memory.
    Cannot delete running sessions - they must be cancelled first.

    Only sessions with status COMPLETED, CANCELLED, ERROR, or PENDING can be deleted.

    Args:
        session_id: Session ID to delete

    Returns:
        DeleteResponse containing session ID, status before deletion, and result message

    Raises:
        HTTPException:
            - 404 if session not found
            - 400 if session is running
    """
    # Attempt to delete the session
    success, error_message, status_before = await session_manager.delete_session(
        session_id
    )

    if not success:
        if status_before == SessionStatus.RUNNING:
            # Session is running - cannot delete
            raise HTTPException(status_code=400, detail=error_message)
        else:
            # Session not found
            raise HTTPException(status_code=404, detail=error_message)

    return DeleteResponse(
        session_id=session_id,
        status=status_before,
        message=f"Session {session_id} deleted successfully",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
