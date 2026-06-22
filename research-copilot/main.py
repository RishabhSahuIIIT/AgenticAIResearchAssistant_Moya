#!/usr/bin/env python3
"""
Research Co-pilot: Multi-Agent System for Research Paper Analysis
Uses Moya framework with TWO Ollama instances:
  - Orchestrator: port 11434
  - Agents: port 11435

Usage:
  python main.py                     # interactive mode
  python main.py /path/to/pdf/folder # pipeline mode (non-interactive)
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

from config import Config
from tools import StorageManager, OllamaError
from agents import PDFParserAgent, SummarizerAgent, SynthesizerAgent, SurveyWriterAgent
from orchestrator import MoyaAgentOrchestrator


class ResearchCopilot:
    """Main application class for the research copilot system."""

    def __init__(self):
        self.config = Config()
        self.run_folder = None
        self.storage = None
        self.orchestrator = None

        # Agents
        self.pdf_parser = None
        self.summarizer = None
        self.synthesizer = None
        self.survey_writer = None

        # State
        self.pipeline_state = {
            "papers_parsed": False,
            "summaries_generated": False,
            "synthesis_done": False,
            "survey_written": False,
        }

        self.parsed_papers = []
        self.summaries = []
        self.synthesis = None
        self.survey = None

    def initialize_run(self):
        """Initialize a new run with timestamped folder."""
        self.run_folder = self.config.create_run_folder()
        self.storage = StorageManager(self.run_folder)

        # Initialize orchestrator (uses port 11434, lighter orchestrator_model_name)
        self.orchestrator = MoyaAgentOrchestrator(
            storage_manager=self.storage,
            model_name=self.config.model_name,
            orchestrator_model_name=self.config.orchestrator_model_name,
            temperature=self.config.temperature,
            seed=self.config.seed,
            orchestrator_host=self.config.orchestrator_ollama_host,
        )

        # Initialize agents (use port 11435)
        self.pdf_parser = PDFParserAgent(self.storage, cache_dir=self.config.pdf_cache_dir)
        self.summarizer = SummarizerAgent(
            self.storage,
            model_name=self.config.model_name,
            ollama_host=self.config.agent_ollama_host,
        )
        self.synthesizer = SynthesizerAgent(
            self.storage,
            model_name=self.config.model_name,
            ollama_host=self.config.agent_ollama_host,
        )
        self.survey_writer = SurveyWriterAgent(
            self.storage,
            model_name=self.config.model_name,
            word_limit=self.config.survey_word_limit,
            ollama_host=self.config.agent_ollama_host,
        )

        self.storage.save_output_description()

        print(f"\n✓ Initialized run folder: {self.run_folder}")
        print(f"  Orchestrator Ollama: {self.config.orchestrator_ollama_host}")
        print(f"  Agent Ollama: {self.config.agent_ollama_host}")
        print(f"  See OUTPUT_DESCRIPTION.md in the run folder for a guide to all output files.")

        self.storage.log_trace("system_init", {
            "run_folder": str(self.run_folder),
            "config": {
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "seed": self.config.seed,
                "orchestrator_host": self.config.orchestrator_ollama_host,
                "agent_host": self.config.agent_ollama_host,
            },
        })

    @staticmethod
    def _validate_pdf_folder(pdf_folder: str) -> bool:
        """Return True if pdf_folder exists, is a directory, and contains PDFs."""
        path = Path(pdf_folder)
        if not path.exists():
            print(f"  ✗ Folder not found: {pdf_folder}")
            return False
        if not path.is_dir():
            print(f"  ✗ Path is not a directory: {pdf_folder}")
            return False
        if not list(path.glob("*.pdf")):
            print(f"  ✗ No PDF files found in: {pdf_folder}")
            return False
        return True

    def parse_papers(self, pdf_folder: str) -> bool:
        """Parse papers from folder."""
        print(f"\n[1/4] Parsing papers from: {pdf_folder}")

        if not self._validate_pdf_folder(pdf_folder):
            return False

        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")

        if next_task != "parse_papers":
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False

        self.parsed_papers = self.pdf_parser.parse_papers(pdf_folder)

        if self.parsed_papers:
            self.pipeline_state["papers_parsed"] = True
            print(f"  ✓ Parsed {len(self.parsed_papers)} papers")
            return True
        else:
            print("  ✗ No papers found or parsing failed")
            return False

    def generate_summaries(self) -> bool:
        """Generate summaries for all papers."""
        if not self.pipeline_state["papers_parsed"]:
            print("\n[2/4] Cannot generate summaries: papers not parsed")
            return False

        print(f"\n[2/4] Generating summaries for {len(self.parsed_papers)} papers")

        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")

        if next_task != "generate_summaries":
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False

        try:
            self.summaries = self.summarizer.summarize_all_papers(self.parsed_papers)
        except OllamaError as e:
            print(f"  ✗ Summarization failed: {e}")
            self.storage.log_trace("pipeline_error", {"stage": "generate_summaries", "error": str(e)})
            return False

        if self.summaries:
            self.pipeline_state["summaries_generated"] = True
            print(f"  ✓ Generated {len(self.summaries)} summaries")
            return True
        else:
            print("  ✗ Summary generation failed")
            return False

    def synthesize_insights(self) -> bool:
        """Synthesize cross-paper insights."""
        if not self.pipeline_state["summaries_generated"]:
            print("\n[3/4] Cannot synthesize: summaries not generated")
            return False

        print("\n[3/4] Synthesizing cross-paper insights")

        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")

        if next_task != "synthesize_insights":
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False

        try:
            self.synthesis = self.synthesizer.synthesize_insights(self.summaries)
        except OllamaError as e:
            print(f"  ✗ Synthesis failed: {e}")
            self.storage.log_trace("pipeline_error", {"stage": "synthesize_insights", "error": str(e)})
            return False

        if self.synthesis:
            self.pipeline_state["synthesis_done"] = True
            print("  ✓ Synthesis complete")
            return True
        else:
            print("  ✗ Synthesis failed")
            return False

    def write_survey(self) -> bool:
        """Generate mini-survey."""
        if not self.pipeline_state["synthesis_done"]:
            print("\n[4/4] Cannot write survey: synthesis not done")
            return False

        print("\n[4/4] Writing mini-survey")

        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")

        if next_task != "write_survey":
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False

        try:
            self.survey = self.survey_writer.generate_mini_survey(
                self.summaries, self.synthesis
            )
        except OllamaError as e:
            print(f"  ✗ Survey writing failed: {e}")
            self.storage.log_trace("pipeline_error", {"stage": "write_survey", "error": str(e)})
            return False

        if self.survey:
            self.pipeline_state["survey_written"] = True
            print("  ✓ Mini-survey complete")
            return True
        else:
            print("  ✗ Survey writing failed")
            return False

    def _print_output_summary(self) -> None:
        """Print a grouped summary of every output file produced in this run."""
        groups = [
            ("Parsed papers (JSON + TXT per paper)", "parsed_*.json"),
            ("Paper summaries", "summary_*.json"),
            ("Cross-paper synthesis", "synthesis_*.json"),
            ("Mini-survey (TXT — primary output)", "mini_survey_*.txt"),
            ("LLM response logs (prompts + raw replies)", "llm_response_*.json"),
        ]
        print("\n" + "─" * 60)
        print("Output files generated:")
        print(f"  Location: {self.run_folder}\n")
        for label, pattern in groups:
            files = list(self.run_folder.glob(pattern))
            if files:
                print(f"  {len(files):2d}  {label}")
        always_present = [
            ("config.json", "run configuration (model, temperature, seed)"),
            ("trace.jsonl", "full execution trace for all agent calls"),
            ("OUTPUT_DESCRIPTION.md", "guide to every file type in this folder"),
        ]
        print()
        for fname, desc in always_present:
            print(f"       {fname:<26} — {desc}")
        print("─" * 60)

    def run_full_pipeline(self, pdf_folder: str):
        """Run the complete pipeline."""
        self.initialize_run()

        print("\n" + "=" * 60)
        print("Research Co-pilot - Multi-Agent System")
        print("  Orchestrator LLM: port 11434")
        print("  Agent LLM: port 11435")
        print("=" * 60)

        success = True
        success = success and self.parse_papers(pdf_folder)
        success = success and self.generate_summaries()
        success = success and self.synthesize_insights()
        success = success and self.write_survey()

        print("\n" + "=" * 60)
        if success:
            print("✓ Pipeline completed successfully!")
        else:
            print("✗ Pipeline completed with errors")
        print(f"  Outputs saved to: {self.run_folder}")
        print("=" * 60)
        self._print_output_summary()

    def interactive_mode(self):
        """Run in interactive terminal mode."""
        self.initialize_run()

        print("\n" + "=" * 60)
        print("Research Co-pilot - Interactive Mode")
        print("=" * 60)
        print(f"Output folder: {self.run_folder}")
        print(f"Orchestrator: {self.config.orchestrator_ollama_host}")
        print(f"Agents: {self.config.agent_ollama_host}\n")

        while True:
            print("\nAvailable actions:")
            print("  1. Parse papers from folder")
            print("  2. Generate summaries")
            print("  3. Synthesize insights")
            print("  4. Write mini-survey")
            print("  5. Run full pipeline")
            print("  6. Show current session state")
            print("  7. Show all previous runs")
            print("  0. Exit")

            choice = input("\nEnter choice: ").strip()

            if choice == "1":
                folder = input("Enter PDF folder path: ").strip()
                if folder:
                    if self.parse_papers(folder):
                        self._print_output_summary()
                else:
                    print("  ✗ No path entered.")

            elif choice == "2":
                if self.generate_summaries():
                    self._print_output_summary()

            elif choice == "3":
                if self.synthesize_insights():
                    self._print_output_summary()

            elif choice == "4":
                if self.write_survey():
                    self._print_output_summary()

            elif choice == "5":
                folder = input("Enter PDF folder path: ").strip()
                if folder:
                    self.run_full_pipeline(folder)
                    break
                else:
                    print("  ✗ No path entered.")

            elif choice == "6":
                print("\nCurrent session state:")
                print(f"  Run folder: {self.run_folder}")
                for key, value in self.pipeline_state.items():
                    status = "✓" if value else "✗"
                    print(f"  {status} {key}")

            elif choice == "7":
                self._show_all_runs()

            elif choice == "0":
                print("\nExiting...")
                break

            else:
                print("\nInvalid choice. Please enter a number from 0 to 7.")


    def _show_all_runs(self):
        """Scan the outputs directory and display the completion state of every past run."""
        run_folders = sorted(self.config.outputs_dir.glob("run_*"), reverse=True)
        if not run_folders:
            print("\n  No previous runs found.")
            return

        print(f"\n{'Run ID':<28}  Stages completed")
        print("  " + "-" * 55)
        for folder in run_folders:
            stages = []
            if any(folder.glob("parsing_summary_*.json")):
                n = len(list(folder.glob("parsed_*.json")))
                stages.append(f"parsed({n})")
            if any(folder.glob("summary_*.json")):
                n = len(list(folder.glob("summary_*.json")))
                stages.append(f"summarized({n})")
            if any(folder.glob("synthesis_*.json")):
                stages.append("synthesized")
            if any(folder.glob("mini_survey_*.txt")):
                stages.append("survey")

            marker = "◀ current" if folder == self.run_folder else ""
            status = " → ".join(stages) if stages else "(empty)"
            print(f"  {folder.name:<28}  {status}  {marker}")


def main():
    """
    Entry point.

    Run without arguments for interactive mode, or pass a PDF folder path for
    automated pipeline mode:

        python main.py /path/to/pdfs
    """
    copilot = ResearchCopilot()

    if len(sys.argv) > 1:
        pdf_folder = sys.argv[1]
        copilot.run_full_pipeline(pdf_folder)
    else:
        copilot.interactive_mode()


if __name__ == "__main__":
    main()
