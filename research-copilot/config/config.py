import os
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
        
        # Model configuration
        self.model_name = "llama3.1"
        self.model_backend = "ollama"
        self.temperature = 0.7
        self.seed = 42
        
        # Ollama instance configuration
        # Orchestrator uses port 11434, Agents use port 11435
        self.orchestrator_ollama_host = "http://127.0.0.1:11434"
        self.agent_ollama_host = "http://127.0.0.1:11435"
        
        # System configuration
        self.max_papers = 6
        self.survey_word_limit = 800
        
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
