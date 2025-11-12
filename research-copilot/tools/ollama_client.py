import ollama
from typing import Optional, Dict, Any

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
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response from Ollama.
        
        Args:
            model: Model name
            prompt: Input prompt
            options: Additional options
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options=options or {}
            )
            return response['response']
        except Exception as e:
            return f"Error calling Ollama at {self.host}: {str(e)}"
    
    def chat(
        self,
        model: str,
        messages: list,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Chat with Ollama using message format.
        
        Args:
            model: Model name
            messages: List of message dictionaries
            options: Additional options
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat(
                model=model,
                messages=messages,
                options=options or {}
            )
            return response['message']['content']
        except Exception as e:
            return f"Error calling Ollama at {self.host}: {str(e)}"


class OrchestratorOllamaClient(OllamaClient):
    """Ollama client specifically for the orchestrator (port 11434)."""
    
    def __init__(self, host: str = "http://127.0.0.1:11434", timeout: float = 300.0):
        super().__init__(host, timeout)


class AgentOllamaClient(OllamaClient):
    """Ollama client specifically for agents (port 11435)."""
    
    def __init__(self, host: str = "http://127.0.0.1:11435", timeout: float = 300.0):
        super().__init__(host, timeout)
