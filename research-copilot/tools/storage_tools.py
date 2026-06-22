import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple


class StorageManager:
    """Manage storage and logging for the system."""

    def __init__(self, run_folder: Path):
        self.run_folder = run_folder
        self.trace_file = run_folder / "trace.jsonl"

    def log_trace(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Append an event to the JSONL trace file.

        Args:
            event_type: Short label for the event (e.g. 'agent_call', 'llm_call')
            data: Arbitrary payload stored alongside the timestamp
        """
        trace_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace_entry) + "\n")

    def save_parsed_paper(self, paper_data: Dict[str, Any]) -> None:
        """
        Write a parsed paper to disk as both JSON (full data) and TXT (readable extract).

        Args:
            paper_data: Dict from PDFParserAgent with keys: filename, text, metadata,
                        num_pages, timestamp
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = paper_data["filename"].replace(".pdf", "")

        json_file = self.run_folder / f"parsed_{stem}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(paper_data, f, indent=2, ensure_ascii=False)

        txt_file = self.run_folder / f"text_{stem}_{timestamp}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(f"Filename: {paper_data['filename']}\n")
            f.write(f"Title: {paper_data['metadata'].get('title', 'Unknown')}\n")
            f.write(f"Author: {paper_data['metadata'].get('author', 'Unknown')}\n")
            f.write(f"Pages: {paper_data['num_pages']}\n")
            f.write(f"Timestamp: {paper_data['timestamp']}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("EXTRACTED TEXT:\n")
            f.write("=" * 80 + "\n\n")
            f.write(paper_data["text"])

        self.log_trace("parsed_paper_saved", {
            "paper": paper_data["filename"],
            "json_file": json_file.name,
            "text_file": txt_file.name,
        })

    def save_parsing_summary(
        self, parsed_papers: List[Dict[str, Any]], pdf_folder: str
    ) -> None:
        """
        Write a JSON summary of the entire PDF-parsing pass.

        Args:
            parsed_papers: List of paper dicts returned by PDFParserAgent
            pdf_folder: Source folder path (stored for traceability)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary = {
            "timestamp": timestamp,
            "pdf_folder": str(pdf_folder),
            "total_papers": len(parsed_papers),
            "papers": [
                {
                    "filename": p["filename"],
                    "title": p["metadata"].get("title", "Unknown"),
                    "author": p["metadata"].get("author", "Unknown"),
                    "num_pages": p["num_pages"],
                    "text_length": len(p["text"]),
                }
                for p in parsed_papers
            ],
        }
        filename = f"parsing_summary_{timestamp}.json"
        with open(self.run_folder / filename, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.log_trace("parsing_summary_saved", {
            "summary_file": filename,
            "total_papers": len(parsed_papers),
        })

    def save_paper_summary(self, paper_name: str, summary: Dict[str, Any]) -> Path:
        """
        Save a single-paper LLM summary to disk.

        Args:
            paper_name: Base filename without extension (used in output filename)
            summary: Summary dict produced by SummarizerAgent

        Returns:
            Path to the saved JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"summary_{paper_name}_{timestamp}.json"
        filepath = self.run_folder / filename
        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)
        return filepath

    def save_synthesis(self, synthesis: Dict[str, Any]) -> Path:
        """
        Save the cross-paper synthesis to disk.

        Args:
            synthesis: Synthesis dict produced by SynthesizerAgent

        Returns:
            Path to the saved JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synthesis_{timestamp}.json"
        filepath = self.run_folder / filename
        with open(filepath, "w") as f:
            json.dump(synthesis, f, indent=2)
        return filepath

    def save_mini_survey(
        self, survey_text: str, metadata: Dict[str, Any]
    ) -> Tuple[Path, Path]:
        """
        Save the mini-survey as both plain text and JSON.

        Args:
            survey_text: Full survey string (narrative + references section)
            metadata: Dict with keys: num_papers, word_limit, papers

        Returns:
            Tuple of (txt_path, json_path)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        txt_filepath = self.run_folder / f"mini_survey_{timestamp}.txt"
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(survey_text)

        json_filepath = self.run_folder / f"mini_survey_{timestamp}.json"
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(
                {"timestamp": timestamp, "text": survey_text, "metadata": metadata},
                f,
                indent=2,
            )

        return txt_filepath, json_filepath

    def save_output_description(self) -> Path:
        """Write OUTPUT_DESCRIPTION.md describing every file type in the run folder."""
        content = """\
# Output Files — Run Description

This folder contains all outputs produced by Research Co-pilot for this run.

## File Types

| File Pattern | Stage | Description |
|---|---|---|
| `config.json` | Init | Run configuration: model name, temperature, seed, Ollama host URLs |
| `trace.jsonl` | All | Append-only execution trace — every agent call, LLM interaction, and decision |
| `OUTPUT_DESCRIPTION.md` | Init | This file |
| `parsing_summary_*.json` | Parse | Overview of the parsing pass: filenames, page counts, character counts |
| `parsed_*.json` | Parse | Full structured data for one paper (extracted text, PDF metadata, page count) |
| `text_*.txt` | Parse | Human-readable plain-text extract for one paper |
| `summary_*.json` | Summarize | LLM-generated structured summary for one paper (methodology, contributions, results, limitations) |
| `synthesis_*.json` | Synthesize | Cross-paper synthesis: shared themes, contradictions, research gaps, future directions |
| `mini_survey_*.txt` | Survey | Final academic mini-survey (≤800 words) with inline citations — the primary readable output |
| `mini_survey_*.json` | Survey | Same survey text with metadata (papers included, word limit, timestamp) |
| `llm_response_*.json` | All LLM | Raw prompt/response pair for one LLM call — useful for debugging and tracing model behaviour |

## Pipeline → Files Produced

```
Parse      →  parsed_*.json  +  text_*.txt  +  parsing_summary_*.json
Summarize  →  summary_*.json (one per paper)  +  llm_response_SummarizerAgent_*.json
Synthesize →  synthesis_*.json  +  llm_response_SynthesizerAgent_*.json
Survey     →  mini_survey_*.txt  +  mini_survey_*.json  +  llm_response_SurveyWriterAgent_*.json
```

## Useful Commands

```bash
# Read the final survey
cat mini_survey_*.txt

# Browse the execution trace
cat trace.jsonl | python3 -m json.tool --no-ensure-ascii | less

# Count LLM calls
grep -c '"event_type": "llm_call"' trace.jsonl

# Inspect a paper summary
cat summary_<papername>_*.json | python3 -m json.tool
```
"""
        filepath = self.run_folder / "OUTPUT_DESCRIPTION.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def save_llm_response(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        ollama_host: str = None,
    ) -> Path:
        """
        Save a raw LLM prompt/response pair for observability.

        Args:
            agent_name: Name of the calling agent
            prompt: Prompt (or its prefix) sent to the LLM
            response: Raw LLM response text
            ollama_host: Ollama host URL used for this call

        Returns:
            Path to the saved JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"llm_response_{agent_name}_{timestamp}.json"
        filepath = self.run_folder / filename
        with open(filepath, "w") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "agent": agent_name,
                    "ollama_host": ollama_host,
                    "prompt": prompt,
                    "response": response,
                },
                f,
                indent=2,
            )
        return filepath
