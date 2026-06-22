import re
from typing import Dict, Any, List

from agents.base_agent import LLMBaseAgent
from tools.storage_tools import StorageManager
from prompts.templates import summarizer_prompt, chunk_summary_prompt, chunk_combine_prompt

# Maximum characters sent to the LLM in a single call.
# 15,000 chars ÷ ~4 chars/token ≈ 3,750 tokens of paper text.
_TEXT_LIMIT = 15_000

# Overlap between consecutive chunks so sentences cut at a boundary are still
# seen in full by at least one chunk.
_CHUNK_OVERLAP = 500

# Ollama generate() options sized to each call's actual token budget.
#
# num_ctx  = total KV-cache window (input tokens + output tokens).
#            Too small → input silently truncated.
#            Too large → wastes RAM with empty KV-cache slots.
# num_predict = maximum output tokens.  Caps runaway generation;
#               if the model finishes naturally before this, no effect.
#
# Single/chunk calls: ~3,750 token input + ~300 prompt + ~1,500 output = 5,550
_SINGLE_CALL_OPTIONS  = {"num_ctx": 6144, "num_predict": 1500}
# Chunk (map step): same input size, shorter partial summary (no conclusions yet)
_CHUNK_MAP_OPTIONS    = {"num_ctx": 6144, "num_predict": 600}
# Combine (reduce step): N × ~600-token partials → typically < 2,000 token input
_CHUNK_REDUCE_OPTIONS = {"num_ctx": 4096, "num_predict": 1500}


class SummarizerAgent(LLMBaseAgent):
    """Agent responsible for generating structured summaries of research papers.

    For papers whose text fits within _TEXT_LIMIT, a single LLM call is made.
    For longer papers a map-reduce strategy is used: each chunk is summarized
    separately (map), then the partial summaries are combined into one final
    structured summary (reduce).  This avoids silent context loss from truncation.
    """

    def __init__(
        self,
        storage_manager: StorageManager,
        model_name: str = "llama3.1",
        ollama_host: str = "http://127.0.0.1:11435",
    ):
        super().__init__("SummarizerAgent", storage_manager, model_name, ollama_host)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def summarize_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a structured 7-section summary for a single paper.

        Uses a single LLM call for short papers and map-reduce for papers
        that exceed _TEXT_LIMIT characters.

        Args:
            paper_data: Parsed paper dict (filename, text, metadata, ...)

        Returns:
            Dict with keys: filename, metadata, summary (LLM text)

        Raises:
            OllamaError: If any LLM call fails after all retries
        """
        self.storage.log_trace("agent_call", {
            "agent": self.name,
            "action": "summarize_paper",
            "paper": paper_data["filename"],
            "ollama_host": self.ollama_host,
        })

        text = self._strip_references(paper_data["text"], paper_data["filename"])
        title = paper_data["metadata"].get("title", "Unknown")

        if len(text) <= _TEXT_LIMIT:
            response = self._summarize_single(title, text, paper_data["filename"])
        else:
            response = self._summarize_chunked(title, text, paper_data["filename"])

        self.storage.save_llm_response(
            self.name, f"[summary for {paper_data['filename']}]", response, self.ollama_host
        )

        summary = {
            "filename": paper_data["filename"],
            "metadata": paper_data["metadata"],
            "summary": response,
        }
        self.storage.save_paper_summary(
            paper_data["filename"].replace(".pdf", ""), summary
        )

        self.storage.log_trace("agent_result", {
            "agent": self.name,
            "action": "summarize_paper",
            "paper": paper_data["filename"],
            "success": True,
        })
        return summary

    def summarize_all_papers(self, parsed_papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate summaries for every paper in the list (sequentially)."""
        return [self.summarize_paper(paper) for paper in parsed_papers]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_references(text: str, filename: str) -> str:
        """Remove the references/bibliography section before sending to the LLM.

        Reference lists contain no semantic meaning for summarization but can
        consume 10-30% of a paper's character count.  We only strip if the
        section header appears in the last 50% of the document to avoid
        accidentally removing a 'Related Work' section near the top.
        """
        pattern = re.compile(
            r'\n\s*(?:REFERENCES|BIBLIOGRAPHY|WORKS CITED|References|Bibliography)\s*\n'
        )
        matches = list(pattern.finditer(text))
        if matches:
            last_match = matches[-1]
            if last_match.start() > len(text) * 0.5:
                stripped = text[:last_match.start()]
                chars_removed = len(text) - len(stripped)
                print(f"  ! Stripped references section from '{filename}' ({chars_removed} chars removed)")
                return stripped
        return text

    def _summarize_single(self, title: str, text: str, filename: str) -> str:
        """Single-call summarization for papers that fit in one context window."""
        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "strategy": "single",
            "paper": filename,
            "text_length": len(text),
            "ollama_host": self.ollama_host,
        })
        prompt = summarizer_prompt(title=title, text=text)
        return self.ollama_client.generate(self.model_name, prompt, options=_SINGLE_CALL_OPTIONS)

    def _summarize_chunked(self, title: str, text: str, filename: str) -> str:
        """Map-reduce summarization for papers that exceed _TEXT_LIMIT.

        Map:    summarize each chunk independently, telling the model more
                content is coming so it does not draw premature conclusions.
        Reduce: combine the ordered partial summaries into one final structured
                summary using the full 7-section format.
        """
        chunks = self._split_into_chunks(text)
        print(f"  ! '{filename}' exceeds {_TEXT_LIMIT} chars — using map-reduce over {len(chunks)} chunks")
        self.storage.log_trace("chunked_summarization_start", {
            "agent": self.name,
            "paper": filename,
            "text_length": len(text),
            "num_chunks": len(chunks),
            "chunk_size": _TEXT_LIMIT,
            "overlap": _CHUNK_OVERLAP,
        })

        # Map step
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            self.storage.log_trace("llm_call", {
                "agent": self.name,
                "strategy": "map",
                "paper": filename,
                "chunk": f"{i + 1}/{len(chunks)}",
                "ollama_host": self.ollama_host,
            })
            print(f"    Summarizing chunk {i + 1}/{len(chunks)}...")
            prompt = chunk_summary_prompt(
                title=title,
                text=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
            )
            partial = self.ollama_client.generate(self.model_name, prompt, options=_CHUNK_MAP_OPTIONS)
            partial_summaries.append(partial)

        # Reduce step
        combined = "\n\n".join([
            f"--- Part {i + 1} of {len(chunks)} ---\n{s}"
            for i, s in enumerate(partial_summaries)
        ])
        self.storage.log_trace("llm_call", {
            "agent": self.name,
            "strategy": "reduce",
            "paper": filename,
            "num_partials": len(partial_summaries),
            "ollama_host": self.ollama_host,
        })
        print(f"    Combining {len(chunks)} partial summaries...")
        prompt = chunk_combine_prompt(title=title, partial_summaries=combined)
        return self.ollama_client.generate(self.model_name, prompt, options=_CHUNK_REDUCE_OPTIONS)

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks of _TEXT_LIMIT characters.

        The overlap ensures that sentences cut at a chunk boundary are fully
        visible to at least one chunk's LLM call.
        """
        chunks = []
        start = 0
        step = _TEXT_LIMIT - _CHUNK_OVERLAP
        while start < len(text):
            chunks.append(text[start: start + _TEXT_LIMIT])
            start += step
        return chunks
