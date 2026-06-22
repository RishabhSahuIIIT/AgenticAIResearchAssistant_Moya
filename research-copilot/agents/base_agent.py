from abc import ABC
from tools.storage_tools import StorageManager
from tools.ollama_client import AgentOllamaClient


class BaseAgent(ABC):
    """Abstract base class shared by all pipeline agents."""

    def __init__(self, name: str, storage: StorageManager):
        self.name = name
        self.storage = storage


class LLMBaseAgent(BaseAgent):
    """Base class for agents that call an LLM through Ollama.

    Agents use port 11435 (separate from the orchestrator on 11434) so LLM
    task execution never blocks orchestration decisions.
    """

    def __init__(
        self,
        name: str,
        storage: StorageManager,
        model_name: str = "llama3.1",
        ollama_host: str = "http://127.0.0.1:11435",
    ):
        super().__init__(name, storage)
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.ollama_client = AgentOllamaClient(host=ollama_host)
