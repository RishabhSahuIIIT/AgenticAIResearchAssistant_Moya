import time
import ollama
from typing import Optional, Dict, Any

# Retry configuration for transient Ollama failures (model loading, timeouts).
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles per attempt: 1s → 2s → 4s


class OllamaError(Exception):
    """Raised when an Ollama API call fails after all retry attempts."""
    pass


class OllamaClient:
    """Wrapper for Ollama client with custom host configuration."""

    def __init__(self, host: str, timeout: float = 300.0):
        """
        Initialize Ollama client.

        Args:
            host: Ollama host URL (e.g., 'http://127.0.0.1:11434')
            timeout: Request timeout in seconds
        """
        self.host = host
        self.timeout = timeout
        self.client = ollama.Client(host=host, timeout=timeout)

    def generate(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a response from Ollama, retrying on transient failures.

        Args:
            model: Model name
            prompt: Input prompt
            options: Additional Ollama options

        Returns:
            Generated text response

        Raises:
            OllamaError: If all retry attempts fail
        """
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.generate(
                    model=model,
                    prompt=prompt,
                    options=options or {},
                )
                return response["response"]
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
        raise OllamaError(
            f"Ollama generate failed after {_MAX_RETRIES} attempts at {self.host}: {last_error}"
        ) from last_error

    def chat(
        self,
        model: str,
        messages: list,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Chat with Ollama using message format, retrying on transient failures.

        Args:
            model: Model name
            messages: List of message dictionaries
            options: Additional Ollama options

        Returns:
            Generated text response

        Raises:
            OllamaError: If all retry attempts fail
        """
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self.client.chat(
                    model=model,
                    messages=messages,
                    options=options or {},
                )
                return response["message"]["content"]
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BASE_DELAY * (2 ** attempt))
        raise OllamaError(
            f"Ollama chat failed after {_MAX_RETRIES} attempts at {self.host}: {last_error}"
        ) from last_error


class OrchestratorOllamaClient(OllamaClient):
    """Ollama client for the orchestrator (port 11434)."""

    def __init__(self, host: str = "http://127.0.0.1:11434", timeout: float = 300.0):
        super().__init__(host, timeout)


class AgentOllamaClient(OllamaClient):
    """Ollama client for task-execution agents (port 11435)."""

    def __init__(self, host: str = "http://127.0.0.1:11435", timeout: float = 300.0):
        super().__init__(host, timeout)
