"""
Sample client code for Claude Agent SDK API

This module provides a sample client implementation
for using the Claude Agent SDK API.
"""

import time
from typing import Dict, Optional

import requests


class ClaudeAgentClient:
    """
    Client class for Claude Agent SDK API

    Wrapper class for interacting with Claude Agent SDK HTTP API.
    Provides functionality for agent execution, status monitoring, cancellation, etc.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client

        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        permission_mode: Optional[str] = None,
        model: Optional[str] = None,
        allowed_tools: Optional[list] = None,
        disallowed_tools: Optional[list] = None,
        env: Optional[Dict[str, str]] = None,
        resume_session_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Execute a new agent session or resume an existing session

        Args:
            prompt: Prompt to send to the agent
            system_prompt: System prompt
            permission_mode: Permission mode (default, acceptEdits, plan, bypassPermissions)
            model: Model to use (sonnet, opus, haiku)
            allowed_tools: List of tool names allowed to be used
            disallowed_tools: List of tool names prohibited from use
            env: Environment variables
            resume_session_id: Session ID to resume (resumes existing session when specified)
            **kwargs: Additional parameters

        Returns:
            Session ID
        """
        data = {"prompt": prompt}

        if system_prompt:
            data["system_prompt"] = system_prompt
        if permission_mode:
            data["permission_mode"] = permission_mode
        if model:
            data["model"] = model
        if resume_session_id:
            data["resume_session_id"] = resume_session_id

        # Add additional parameters
        data.update(kwargs)

        response = requests.post(f"{self.base_url}/execute/", json=data)
        response.raise_for_status()

        result = response.json()
        return result["session_id"]

    def get_status(self, session_id: str) -> Dict:
        """
        Get session status

        Args:
            session_id: Session ID

        Returns:
            Status information
        """
        response = requests.get(f"{self.base_url}/status/{session_id}")
        response.raise_for_status()
        result = response.json()

        # Debug: Display response structure
        print(f"DEBUG: get_status response type: {type(result)}")
        if isinstance(result, dict):
            print(f"DEBUG: get_status keys: {list(result.keys())}")
            if "result" in result:
                print(f"DEBUG: result field type: {type(result['result'])}")
                print(f"DEBUG: result field content: {result['result']}")
        else:
            print(f"DEBUG: Unexpected response type: {result}")

        return result

    def cleanup_sessions(self, max_age_hours: int = 0) -> Dict:
        """
        Clean up completed sessions

        Args:
            max_age_hours: Maximum age of sessions to keep (default: 0 hours to remove all completed sessions)

        Returns:
            Cleanup result
        """
        params = {"max_age_hours": max_age_hours}
        response = requests.delete(f"{self.base_url}/sessions/cleanup", params=params)
        response.raise_for_status()
        return response.json()

    def cancel(self, session_id: str) -> Dict:
        """
        Cancel a running session

        Args:
            session_id: Session ID

        Returns:
            Cancellation result
        """
        response = requests.post(f"{self.base_url}/cancel/{session_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        session_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
    ) -> Dict:
        """
        Wait for session completion

        Args:
            session_id: Session ID
            poll_interval: Polling interval (seconds)
            timeout: Timeout duration (seconds, no timeout if None)

        Returns:
            Final status information
        """
        start_time = time.time()

        while True:
            status = self.get_status(session_id)

            if status["status"] in ["completed", "error", "cancelled"]:
                return status

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"Session {session_id} did not complete within {timeout} seconds"
                )

            time.sleep(poll_interval)

    def list_sessions(self) -> list:
        """
        List all sessions with detailed information

        Returns:
            List of session detailed information
        """
        response = requests.get(f"{self.base_url}/sessions/")
        response.raise_for_status()
        return response.json()


def main():
    """Demonstration of usage examples

    Shows various usage patterns of the Claude Agent SDK API client.
    """
    try:
        # Create client
        client = ClaudeAgentClient()
        print("Testing connection to server...")

        # Test if server is running
        import requests

        response = requests.get(f"{client.base_url}/")
        if response.status_code == 200:
            print(f"✓ Server is running: {client.base_url}")
        else:
            print(f"⚠ Server error: {response.status_code}")
            return
    except Exception as e:
        print(f"Error: Cannot connect to server: {e}")
        print("Please verify that the FastAPI server is running.")
        return

    # Example 1: Simple execution
    print("=" * 80)
    print("Example 1: Simple execution")
    print("Prompt: Please introduce yourself.")
    print("=" * 80)

    session_id = client.execute(
        prompt="Please introduce yourself.",
        system_prompt="Please respond in English.",
        permission_mode="acceptEdits",
        model="sonnet",
    )
    print(f"Session ID: {session_id}")

    # Wait for completion
    print("\nWaiting for completion...")
    final_status = client.wait_for_completion(session_id)
    print(f"Final status: {final_status}")

    if final_status.get("result"):
        print(f"Result: {final_status}")

    if final_status.get("error"):
        print(f"Error: {final_status['error']}")

    print(f"Execution time: {final_status.get('duration_ms')}ms")
    print(f"Cost: ${final_status.get('total_cost_usd')}")

    # Example 3: Cancellation
    print("\n" + "=" * 80)
    print("Example 3: Cancellation")
    print("=" * 80)

    session_id = client.execute(
        prompt="Please count from 1 to 1000",
        permission_mode="acceptEdits",
    )
    print(f"Session ID: {session_id}")

    # Wait a bit
    time.sleep(5)

    # Cancel
    print("\nCancelling session...")
    cancel_result = client.cancel(session_id)
    print(f"Cancellation result: {cancel_result}")

    # List all sessions
    print("\n" + "=" * 80)
    print("All sessions:")
    print("=" * 80)
    sessions = client.list_sessions()
    print(f"Total sessions: {len(sessions)}")
    for session in sessions:
        session_id = session["session_id"]
        status = session["status"]
        prompt_preview = (
            session["prompt"][:50] + "..."
            if len(session["prompt"]) > 50
            else session["prompt"]
        )
        print(f"- {session_id}: {status} | {prompt_preview}")

    # Example 4: Session resume
    print("\n" + "=" * 80)
    print("Example 4: Session resume")
    print("=" * 80)

    # Create first session
    first_session_id = client.execute(
        prompt="I am is0383kk. Please remember this.",
        permission_mode="acceptEdits",
    )
    print(f"First session ID: {first_session_id}")

    # Wait for completion
    print("Waiting for first session to complete...")
    first_status = client.wait_for_completion(first_session_id)

    if (
        first_status["status"] == "completed"
        and first_status.get("result")
        and first_status["result"].get("session_id")
    ):
        # Resume session if Claude session ID was obtained
        print(f"Claude session ID: {first_status['result']['session_id']}")
        print(f"First execution result: {first_status}")

        # Send different prompt to same session (resume)
        resumed_session_id = client.execute(
            prompt="What was my name again?",
            resume_session_id=first_session_id,  # Resume existing session
        )
        print(f"Resumed session ID: {resumed_session_id} (should be the same ID)")

        # Wait for resumed session completion
        print("Waiting for resumed session to complete...")
        resumed_status = client.wait_for_completion(resumed_session_id)
        print(f"Resumed session final status: {resumed_status}")
    else:
        print(
            "First session did not complete or Claude session ID could not be obtained"
        )

    # Example 5: Cleanup
    print("\n" + "=" * 80)
    print("Example 5: Cleanup completed sessions")
    print("=" * 80)

    # Session count before cleanup
    sessions_before = client.list_sessions()
    print(f"Sessions before cleanup: {len(sessions_before)}")

    # Clean up completed sessions
    cleanup_result = client.cleanup_sessions(max_age_hours=0)
    print(f"Cleanup result: {cleanup_result}")

    # Session count after cleanup
    sessions_after = client.list_sessions()
    print(f"Sessions after cleanup: {len(sessions_after)}")

    print("\nTesting completed!")


if __name__ == "__main__":
    main()
