from typing import Dict, Any, List
from tools.storage_tools import StorageManager
from tools.ollama_client import AgentOllamaClient

class SurveyWriterAgent:
    """Agent responsible for generating mini-surveys."""
    
    def __init__(
        self, 
        storage_manager: StorageManager, 
        model_name: str = "llama3.1",
        word_limit: int = 800,
        ollama_host: str = "http://127.0.0.1:11435"
    ):
        self.name = "SurveyWriterAgent"
        self.storage = storage_manager
        self.model_name = model_name
        self.word_limit = word_limit
        self.ollama_host = ollama_host
        self.ollama_client = AgentOllamaClient(host=ollama_host)
        
    def generate_mini_survey(
        self, 
        summaries: List[Dict[str, Any]], 
        synthesis: Dict[str, Any]
    ) -> str:
        """
        Generate a mini-survey with inline citations.
        
        Args:
            summaries: List of paper summaries
            synthesis: Cross-paper synthesis
            
        Returns:
            Mini-survey text
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "generate_mini_survey",
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host
        })
        
        # Prepare paper references
        paper_refs = "\n".join([
            f"[{i+1}] {s['filename']}: {s['metadata'].get('title', 'Unknown')}"
            for i, s in enumerate(summaries)
        ])
        
        combined_content = f"""
Synthesis:
{synthesis['insights'][:2000]}

Individual Papers:
{paper_refs}
"""
        
        prompt = f"""You are a technical writer creating a mini-survey paper. Write a comprehensive survey (maximum {self.word_limit} words) based on the following research papers.

{combined_content}

Requirements:
1. Start with an introduction to the topic
2. Discuss key themes and methodologies
3. Present main findings across papers
4. Identify research gaps
5. Conclude with future directions
6. Use inline citations like [1], [2], etc. when referencing papers
7. Keep it under {self.word_limit} words
8. Write in academic style

Write the mini-survey now:"""

        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "model": self.model_name,
            "word_limit": self.word_limit,
            "ollama_host": self.ollama_host
        })
        
        response = self.ollama_client.generate(self.model_name, prompt)
        
        # Add references section
        full_survey = f"{response}\n\n## References\n{paper_refs}"
        
        # Save LLM response
        self.storage.save_llm_response(
            self.name, 
            prompt[:500], 
            full_survey,
            self.ollama_host
        )
        
        # Save mini-survey
        metadata = {
            "num_papers": len(summaries),
            "word_limit": self.word_limit,
            "papers": [s["filename"] for s in summaries]
        }
        self.storage.save_mini_survey(full_survey, metadata)
        
        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "generate_mini_survey",
            "success": True
        })
        
        return full_survey
