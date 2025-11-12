from typing import Dict, Any, List
from tools.storage_tools import StorageManager
from tools.ollama_client import AgentOllamaClient

class SummarizerAgent:
    """Agent responsible for generating structured summaries."""
    
    def __init__(
        self, 
        storage_manager: StorageManager, 
        model_name: str = "llama3.1",
        ollama_host: str = "http://127.0.0.1:11435"
    ):
        self.name = "SummarizerAgent"
        self.storage = storage_manager
        self.model_name = model_name
        self.ollama_host = ollama_host
        self.ollama_client = AgentOllamaClient(host=ollama_host)
        
    def summarize_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate structured summary for a single paper.
        
        Args:
            paper_data: Parsed paper data
            
        Returns:
            Structured summary
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "summarize_paper",
            "paper": paper_data["filename"],
            "ollama_host": self.ollama_host
        })
        
        # Truncate text if too long (Ollama has context limits)
        text = paper_data["text"][:15000]
        
        prompt = f"""You are a research paper analyzer. Analyze the following research paper and provide a structured summary.

Paper Title: {paper_data['metadata'].get('title', 'Unknown')}
Paper Text:
{text}

Provide a structured summary with the following sections:
1. Title and Authors
2. Main Research Question/Problem
3. Key Contributions
4. Methodology/Approach
5. Main Results/Findings
6. Limitations
7. Future Work

Format your response as clear, concise bullet points for each section."""

        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "model": self.model_name,
            "paper": paper_data["filename"],
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
        
        summary = {
            "filename": paper_data["filename"],
            "metadata": paper_data["metadata"],
            "summary": response
        }
        
        # Save individual summary
        self.storage.save_paper_summary(
            paper_data["filename"].replace(".pdf", ""),
            summary
        )
        
        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "summarize_paper",
            "paper": paper_data["filename"],
            "success": True
        })
        
        return summary
    
    def summarize_all_papers(self, parsed_papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate summaries for all papers."""
        summaries = []
        for paper in parsed_papers:
            summary = self.summarize_paper(paper)
            summaries.append(summary)
        return summaries
