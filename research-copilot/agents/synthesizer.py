from typing import Dict, Any, List
from tools.storage_tools import StorageManager
from tools.ollama_client import AgentOllamaClient

class SynthesizerAgent:
    """Agent responsible for synthesizing cross-paper insights."""
    
    def __init__(
        self, 
        storage_manager: StorageManager, 
        model_name: str = "llama3.1",
        ollama_host: str = "http://127.0.0.1:11435"
    ):
        self.name = "SynthesizerAgent"
        self.storage = storage_manager
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.ollama_client = AgentOllamaClient(host=ollama_host)
        
    def synthesize_insights(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize cross-paper insights and identify research gaps.
        
        Args:
            summaries: List of paper summaries
            
        Returns:
            Synthesis with insights and gaps
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "synthesize_insights",
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host
        })
        
        # Combine summaries
        combined_summaries = "\n\n".join([
            f"Paper {i+1}: {s['filename']}\n{s['summary'][:1000]}"
            for i, s in enumerate(summaries)
        ])
        
        prompt = f"""You are a research analyst. Based on the following paper summaries, identify:

1. Common themes and trends across papers
2. Key methodologies used
3. Main findings and contributions
4. Research gaps and unexplored areas
5. Contradictions or conflicting results
6. Potential future research directions

Paper Summaries:
{combined_summaries}

Provide a comprehensive synthesis organized into these sections."""

        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "model": self.model_name,
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host
        })
        
        response = self.ollama_client.generate(self.model_name, prompt)
        
        # Save LLM response
        self.storage.save_llm_response(
            self.name, 
            prompt[:500], 
            response,
            self.ollama_host
        )
        
        synthesis = {
            "num_papers": len(summaries),
            "papers": [s["filename"] for s in summaries],
            "insights": response
        }
        
        # Save synthesis
        self.storage.save_synthesis(synthesis)
        
        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "synthesize_insights",
            "success": True
        })
        
        return synthesis
