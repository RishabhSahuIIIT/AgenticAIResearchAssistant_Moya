from typing import Dict, Any, List

from agents.base_agent import LLMBaseAgent
from tools.storage_tools import StorageManager
from prompts.templates import survey_writer_prompt

# Survey input is concise: synthesis excerpt (~500 tokens) + refs (~50 tokens/paper × 6)
# + prompt overhead (~200 tokens) ≈ 1,000 input tokens.
# Output: ≤800 words ≈ 1,100 tokens + references section ≈ 300 tokens → cap at 1,600.
_SURVEY_OPTIONS = {"num_ctx": 4096, "num_predict": 1600}


class SurveyWriterAgent(LLMBaseAgent):
    """Agent responsible for generating a mini-survey with inline citations."""

    def __init__(
        self,
        storage_manager: StorageManager,
        model_name: str = "llama3.1",
        word_limit: int = 800,
        ollama_host: str = "http://127.0.0.1:11435",
    ):
        super().__init__("SurveyWriterAgent", storage_manager, model_name, ollama_host)
        self.word_limit = word_limit

    def generate_mini_survey(
        self,
        summaries: List[Dict[str, Any]],
        synthesis: Dict[str, Any],
    ) -> str:
        """
        Write a mini-survey (≤ word_limit words) with inline [N] citations.

        Args:
            summaries: Per-paper summaries from SummarizerAgent
            synthesis: Cross-paper synthesis from SynthesizerAgent

        Returns:
            Full survey text including a References section

        Raises:
            OllamaError: If the LLM call fails after all retries
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "generate_mini_survey",
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host,
        })

        paper_refs = "\n".join([
            f"[{i + 1}] {s['filename']}: {s['metadata'].get('title', 'Unknown')}"
            for i, s in enumerate(summaries)
        ])
        combined_content = (
            f"Synthesis:\n{synthesis['insights'][:2000]}\n\nIndividual Papers:\n{paper_refs}"
        )
        prompt = survey_writer_prompt(combined_content, self.word_limit)

        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "model": self.model_name,
            "word_limit": self.word_limit,
            "ollama_host": self.ollama_host,
        })

        response = self.ollama_client.generate(self.model_name, prompt, options=_SURVEY_OPTIONS)
        full_survey = f"{response}\n\n## References\n{paper_refs}"

        self.storage.save_llm_response(self.name, prompt[:500], full_survey, self.ollama_host)
        self.storage.save_mini_survey(
            full_survey,
            {
                "num_papers": len(summaries),
                "word_limit": self.word_limit,
                "papers": [s["filename"] for s in summaries],
            },
        )

        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "generate_mini_survey",
            "success": True,
        })
        return full_survey
