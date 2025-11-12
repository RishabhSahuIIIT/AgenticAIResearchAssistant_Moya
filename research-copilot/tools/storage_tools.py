import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

class StorageManager:
    """Manage storage and logging for the system."""
    
    def __init__(self, run_folder: Path):
        self.run_folder = run_folder
        self.trace_file = run_folder / "trace.jsonl"
        
    def log_trace(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event to the trace file.
        
        Args:
            event_type: Type of event (e.g., 'agent_call', 'tool_call', 'decision')
            data: Event data to log
        """
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(trace_entry) + "\n")
    
    def save_paper_summary(self, paper_name: str, summary: Dict[str, Any]):
        """Save summary for a single paper."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{paper_name}_{timestamp}.json"
        filepath = self.run_folder / filename
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return filepath
    
    def save_synthesis(self, synthesis: Dict[str, Any]):
        """Save cross-paper synthesis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synthesis_{timestamp}.json"
        filepath = self.run_folder / filename
        
        with open(filepath, 'w') as f:
            json.dump(synthesis, f, indent=2)
        
        return filepath
    
    def save_mini_survey(self, survey_text: str, metadata: Dict[str, Any]):
        """Save the mini-survey output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as text
        txt_filename = f"mini_survey_{timestamp}.txt"
        txt_filepath = self.run_folder / txt_filename
        with open(txt_filepath, 'w') as f:
            f.write(survey_text)
        
        # Save metadata
        json_filename = f"mini_survey_{timestamp}.json"
        json_filepath = self.run_folder / json_filename
        survey_data = {
            "timestamp": timestamp,
            "text": survey_text,
            "metadata": metadata
        }
        with open(json_filepath, 'w') as f:
            json.dump(survey_data, f, indent=2)
        
        return txt_filepath, json_filepath
    
    def save_llm_response(self, agent_name: str, prompt: str, response: str, ollama_host: str = None):
        """Save LLM responses for observability."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"llm_response_{agent_name}_{timestamp}.json"
        filepath = self.run_folder / filename
        
        data = {
            "timestamp": timestamp,
            "agent": agent_name,
            "ollama_host": ollama_host,
            "prompt": prompt,
            "response": response
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
