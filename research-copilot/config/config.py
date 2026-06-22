import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration management for the research copilot system."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.outputs_dir = self.base_dir / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

        # Task-agent model — used by SummarizerAgent, SynthesizerAgent, SurveyWriterAgent.
        # Keep in sync with AGENT_MODEL in setup_ollama.sh.
        self.model_name = "llama3.1"

        # Orchestrator model — only needs to route between four agent names, so a
        # lighter model is sufficient and reduces latency for each routing call.
        # Keep in sync with ORCH_MODEL in setup_ollama.sh.
        self.orchestrator_model_name = "llama3.2"

        self.model_backend = "ollama"
        self.temperature = 0.7
        self.seed = 42

        # Two separate Ollama instances prevent the orchestrator's LLM calls from
        # blocking task-execution agents and vice versa.
        self.orchestrator_ollama_host = "http://127.0.0.1:11434"
        self.agent_ollama_host = "http://127.0.0.1:11435"

        # Parsed PDF cache — avoids re-extracting text when only prompts change.
        self.pdf_cache_dir = self.base_dir / "pdf_cache"
        self.pdf_cache_dir.mkdir(exist_ok=True)

        # System configuration
        self.max_papers = 6
        self.survey_word_limit = 800

        self._validate()
        
    def _validate(self) -> None:
        """Raise ValueError if any configuration value is invalid."""
        if not self.model_name:
            raise ValueError("model_name must not be empty")
        if not self.orchestrator_model_name:
            raise ValueError("orchestrator_model_name must not be empty")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError(f"temperature must be in [0, 2], got {self.temperature}")
        if self.max_papers < 1:
            raise ValueError(f"max_papers must be >= 1, got {self.max_papers}")
        if self.survey_word_limit < 1:
            raise ValueError(f"survey_word_limit must be >= 1, got {self.survey_word_limit}")
        for label, host in [
            ("orchestrator_ollama_host", self.orchestrator_ollama_host),
            ("agent_ollama_host", self.agent_ollama_host),
        ]:
            if not host.startswith("http"):
                raise ValueError(f"{label} must be a valid HTTP URL, got '{host}'")

    def create_run_folder(self) -> Path:
        """Create a new timestamped folder for this run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = self.outputs_dir / f"run_{timestamp}"
        run_folder.mkdir(parents=True, exist_ok=True)
        
        # Save run configuration
        config_data = {
            "timestamp": timestamp,
            "model_name": self.model_name,
            "model_backend": self.model_backend,
            "temperature": self.temperature,
            "seed": self.seed,
            "max_papers": self.max_papers,
            "survey_word_limit": self.survey_word_limit,
            "orchestrator_host": self.orchestrator_ollama_host,
            "agent_host": self.agent_ollama_host
        }
        
        config_file = run_folder / "config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return run_folder
    
    def get_trace_file(self, run_folder: Path) -> Path:
        """Get trace.jsonl file path for logging."""
        return run_folder / "trace.jsonl"
