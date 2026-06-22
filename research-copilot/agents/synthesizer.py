from typing import Dict, Any, List

from agents.base_agent import LLMBaseAgent
from tools.storage_tools import StorageManager
from prompts.templates import synthesizer_prompt

# Per-paper summary character limit sent to the synthesis prompt.
# 3,000 chars × 6 papers ≈ 4,500 tokens input + ~300 prompt tokens.
_SUMMARY_LIMIT = 3_000

# num_ctx: 4,800 input tokens + ~1,500 output tokens = 6,300 → round up to 6144
# num_predict: synthesis is dense; 1,500 tokens ≈ ~1,100 words, more than enough
_SYNTHESIZE_OPTIONS = {"num_ctx": 6144, "num_predict": 1500}


class SynthesizerAgent(LLMBaseAgent):
    """Agent responsible for synthesizing cross-paper insights."""

    def __init__(
        self,
        storage_manager: StorageManager,
        model_name: str = "llama3.1",
        ollama_host: str = "http://127.0.0.1:11435",
    ):
        super().__init__("SynthesizerAgent", storage_manager, model_name, ollama_host)

    def synthesize_insights(self, summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize cross-paper insights and identify research gaps.

        Each paper summary is truncated to _SUMMARY_LIMIT chars so the combined
        prompt fits within the Ollama context window.

        Args:
            summaries: List of paper summary dicts from SummarizerAgent

        Returns:
            Dict with keys: num_papers, papers, insights (LLM text)

        Raises:
            OllamaError: If the LLM call fails after all retries
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "synthesize_insights",
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host,
        })

        truncated_papers = [s for s in summaries if len(s["summary"]) > _SUMMARY_LIMIT]
        if truncated_papers:
            names = [s["filename"] for s in truncated_papers]
            print(
                f"  ! Truncating {len(truncated_papers)} paper summaries to {_SUMMARY_LIMIT} chars each for synthesis (context window limit): {names}"
            )
            self.storage.log_trace("text_truncated", {
                "agent": self.name,
                "papers_truncated": names,
                "truncated_to": _SUMMARY_LIMIT,
            })

        combined_summaries = "\n\n".join([
            f"Paper {i + 1}: {s['filename']}\n{s['summary'][:_SUMMARY_LIMIT]}"
            for i, s in enumerate(summaries)
        ])

        prompt = synthesizer_prompt(combined_summaries)

        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "model": self.model_name,
            "num_papers": len(summaries),
            "ollama_host": self.ollama_host,
        })

        response = self.ollama_client.generate(self.model_name, prompt, options=_SYNTHESIZE_OPTIONS)
        self.storage.save_llm_response(self.name, prompt[:500], response, self.ollama_host)

        synthesis = {
            "num_papers": len(summaries),
            "papers": [s["filename"] for s in summaries],
            "insights": response,
        }
        self.storage.save_synthesis(synthesis)

        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "synthesize_insights",
            "success": True,
        })
        return synthesis
