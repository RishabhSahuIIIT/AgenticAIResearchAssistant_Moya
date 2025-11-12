#!/usr/bin/env python3
"""
Research Co-pilot: Multi-Agent System for Research Paper Analysis
Uses Moya framework with TWO Ollama instances:
  - Orchestrator: port 11434
  - Agents: port 11435
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

from config import Config
from tools import StorageManager
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
            'papers_parsed': False,
            'summaries_generated': False,
            'synthesis_done': False,
            'survey_written': False
        }
        
        self.parsed_papers = []
        self.summaries = []
        self.synthesis = None
        self.survey = None
    def initialize_run(self):
        """Initialize a new run with timestamped folder."""
        self.run_folder = self.config.create_run_folder()
        self.storage = StorageManager(self.run_folder)
        
        # Initialize orchestrator (uses port 11434)
        self.orchestrator = MoyaAgentOrchestrator(
            storage_manager=self.storage,
            model_name=self.config.model_name,
            temperature=self.config.temperature,
            seed=self.config.seed,
            orchestrator_host=self.config.orchestrator_ollama_host
        )
        
        # Initialize agents (use port 11435)
        self.pdf_parser = PDFParserAgent(self.storage)
        
        # Fix: Use keyword arguments for ollama_host
        self.summarizer = SummarizerAgent(
            self.storage,
            model_name=self.config.model_name,
            ollama_host=self.config.agent_ollama_host
        )
        
        self.synthesizer = SynthesizerAgent(
            self.storage,
            model_name=self.config.model_name,
            ollama_host=self.config.agent_ollama_host
        )
        
        self.survey_writer = SurveyWriterAgent(
            self.storage,
            model_name=self.config.model_name,
            word_limit=self.config.survey_word_limit,
            ollama_host=self.config.agent_ollama_host
        )
        
        print(f"\n✓ Initialized run folder: {self.run_folder}")
        print(f"  Orchestrator Ollama: {self.config.orchestrator_ollama_host}")
        print(f"  Agent Ollama: {self.config.agent_ollama_host}")
        
        self.storage.log_trace("system_init", {
            "run_folder": str(self.run_folder),
            "config": {
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "seed": self.config.seed,
                "orchestrator_host": self.config.orchestrator_ollama_host,
                "agent_host": self.config.agent_ollama_host
            }
        })
    
    
    def parse_papers(self, pdf_folder: str) -> bool:
        """Parse papers from folder."""
        print(f"\n[1/4] Parsing papers from: {pdf_folder}")
        
        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")
        
        if next_task != 'parse_papers':
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False
        
        self.parsed_papers = self.pdf_parser.parse_papers(pdf_folder)
        
        if self.parsed_papers:
            self.pipeline_state['papers_parsed'] = True
            print(f"  ✓ Parsed {len(self.parsed_papers)} papers")
            return True
        else:
            print("  ✗ No papers found or parsing failed")
            return False
    
    def generate_summaries(self) -> bool:
        """Generate summaries for all papers."""
        if not self.pipeline_state['papers_parsed']:
            print("\n[2/4] Cannot generate summaries: papers not parsed")
            return False
        
        print(f"\n[2/4] Generating summaries for {len(self.parsed_papers)} papers")
        
        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")
        
        if next_task != 'generate_summaries':
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False
        
        self.summaries = self.summarizer.summarize_all_papers(self.parsed_papers)
        
        if self.summaries:
            self.pipeline_state['summaries_generated'] = True
            print(f"  ✓ Generated {len(self.summaries)} summaries")
            return True
        else:
            print("  ✗ Summary generation failed")
            return False
    
    def synthesize_insights(self) -> bool:
        """Synthesize cross-paper insights."""
        if not self.pipeline_state['summaries_generated']:
            print("\n[3/4] Cannot synthesize: summaries not generated")
            return False
        
        print("\n[3/4] Synthesizing cross-paper insights")
        
        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")
        
        if next_task != 'synthesize_insights':
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False
        
        self.synthesis = self.synthesizer.synthesize_insights(self.summaries)
        
        if self.synthesis:
            self.pipeline_state['synthesis_done'] = True
            print("  ✓ Synthesis complete")
            return True
        else:
            print("  ✗ Synthesis failed")
            return False
    
    def write_survey(self) -> bool:
        """Generate mini-survey."""
        if not self.pipeline_state['synthesis_done']:
            print("\n[4/4] Cannot write survey: synthesis not done")
            return False
        
        print("\n[4/4] Writing mini-survey")
        
        next_task = self.orchestrator.decide_next_task(self.pipeline_state)
        print(f"  → Orchestrator decision: {next_task}")
        
        if next_task != 'write_survey':
            print(f"  → Skipping (orchestrator chose: {next_task})")
            return False
        
        self.survey = self.survey_writer.generate_mini_survey(
            self.summaries,
            self.synthesis
        )
        
        if self.survey:
            self.pipeline_state['survey_written'] = True
            print("  ✓ Mini-survey complete")
            return True
        else:
            print("  ✗ Survey writing failed")
            return False
    
    def run_full_pipeline(self, pdf_folder: str):
        """Run the complete pipeline."""
        self.initialize_run()
        
        print("\n" + "="*60)
        print("Research Co-pilot - Multi-Agent System")
        print("  Orchestrator LLM: port 11434")
        print("  Agent LLM: port 11435")
        print("="*60)
        
        # Execute pipeline with orchestrator decisions
        success = True
        success = success and self.parse_papers(pdf_folder)
        success = success and self.generate_summaries()
        success = success and self.synthesize_insights()
        success = success and self.write_survey()
        
        if success:
            print("\n" + "="*60)
            print("✓ Pipeline completed successfully!")
            print(f"  Outputs saved to: {self.run_folder}")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("✗ Pipeline completed with errors")
            print(f"  Check logs in: {self.run_folder}")
            print("="*60)
    
    def interactive_mode(self):
        """Run in interactive terminal mode."""
        self.initialize_run()
        
        print("\n" + "="*60)
        print("Research Co-pilot - Interactive Mode")
        print("="*60)
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
            print("  6. Show current state")
            print("  0. Exit")
            
            choice = input("\nEnter choice: ").strip()
            
            if choice == "1":
                folder = input("Enter PDF folder path: ").strip()
                self.parse_papers(folder)
            
            elif choice == "2":
                self.generate_summaries()
            
            elif choice == "3":
                self.synthesize_insights()
            
            elif choice == "4":
                self.write_survey()
            
            elif choice == "5":
                folder = input("Enter PDF folder path: ").strip()
                self.run_full_pipeline(folder)
                break
            
            elif choice == "6":
                print("\nCurrent State:")
                for key, value in self.pipeline_state.items():
                    status = "✓" if value else "✗"
                    print(f"  {status} {key}: {value}")
            
            elif choice == "0":
                print("\nExiting...")
                break
            
            else:
                print("\nInvalid choice. Please try again.")


def main():
    """Main entry point."""
    copilot = ResearchCopilot()
    
    if len(sys.argv) > 1:
        # Command-line mode with PDF folder argument
        pdf_folder = sys.argv[1]
        copilot.run_full_pipeline(pdf_folder)
    else:
        # Interactive mode
        copilot.interactive_mode()


if __name__ == "__main__":
    main()
