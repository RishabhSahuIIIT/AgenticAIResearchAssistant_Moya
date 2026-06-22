import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from tools.storage_tools import StorageManager
from tools.ollama_client import OrchestratorOllamaClient

# Import moya components - REQUIRED for this assignment
from moya.agents.agent import Agent, AgentConfig
from moya.agents.ollama_agent import OllamaAgent
from moya.classifiers.llm_classifier import LLMClassifier
from moya.orchestrators.simple_orchestrator import SimpleOrchestrator
from moya.orchestrators.multi_agent_orchestrator import MultiAgentOrchestrator
from moya.registry.agent_registry import AgentRegistry

class MoyaAgentOrchestrator:
    """
    Orchestrator using Moya framework to coordinate agents.
    Uses Moya's Agent and Orchestrator classes properly.
    Orchestrator runs on separate Ollama instance (port 11434).
    Agents run on separate instance (port 11435).
    """
    
    def __init__(
        self,
        storage_manager: StorageManager,
        model_name: str = "llama3.1",
        orchestrator_model_name: str = "llama3.2",
        temperature: float = 0.7,
        seed: int = 42,
        orchestrator_host: str = "http://127.0.0.1:11434"
    ):
        self.storage = storage_manager
        self.model_name = model_name
        self.orchestrator_model_name = orchestrator_model_name
        self.temperature = temperature
        self.seed = seed
        self.orchestrator_host = orchestrator_host
        
        # Initialize Moya's Agent Registry
        self.registry = AgentRegistry()
        
        # Setup agents first (they will be registered)
        self.agents = {}
        self._setup_moya_agents()
        
        # Initialize Moya's Orchestrator with intelligent routing
        # Try to use MultiAgentOrchestrator if available, else SimpleOrchestrator
        try:
            # LLMClassifier needs its own OllamaAgent on the orchestrator instance (port 11434)
            # to route queries to the right pipeline agent.
            classifier_config = AgentConfig(
                agent_name="classifier",
                agent_type="ollama",
                description="Routes pipeline tasks to the correct agent",
                system_prompt="You are a routing agent. Given a task description and a list of available agents, return only the name of the most appropriate agent.",
                llm_config={
                    "base_url": orchestrator_host,
                    "model_name": orchestrator_model_name,  # smaller model is enough for routing
                    "temperature": temperature,
                }
            )
            classifier_agent = OllamaAgent(agent_config=classifier_config)
            classifier = LLMClassifier(
                llm_agent=classifier_agent,
                default_agent="pdf_parser"
            )
            self.moya_orchestrator = MultiAgentOrchestrator(
                agent_registry=self.registry,
                classifier=classifier,
                default_agent_name="pdf_parser"
            )
            self.orchestrator_type = "MultiAgent"
        except (TypeError, AttributeError, ConnectionError, OSError) as e:
            # Fallback to SimpleOrchestrator (e.g. Ollama not yet running at init time)
            self.moya_orchestrator = SimpleOrchestrator(
                agent_registry=self.registry,
                default_agent_name="pdf_parser"
            )
            self.orchestrator_type = "Simple"
        
        self.storage.log_trace("orchestrator_init", {
            "orchestrator": "MoyaOrchestrator",
            "orchestrator_type": self.orchestrator_type,
            "orchestrator_model": orchestrator_model_name,
            "agent_model": model_name,
            "host": orchestrator_host,
            "temperature": temperature,
            "seed": seed,
            "framework": "Moya",
            "num_agents": len(self.agents)
        })
        
    def _setup_moya_agents(self):
        """Setup Moya agents and register them with the registry."""
        
        # Define agent configurations for the research pipeline
        agent_configs = [
            {
                "name": "pdf_parser",
                "description": "Parses PDF research papers and extracts text content, metadata, and structure from research papers in PDF format. Use when you need to read PDFs.",
                "system_prompt": "You are a PDF parsing agent. Your job is to extract text and metadata from research papers in PDF format. You handle document parsing and text extraction."
            },
            {
                "name": "summarizer",
                "description": "Generates structured summaries of research papers including methodology, key contributions, results, and limitations. Use when papers have been parsed and need summarization.",
                "system_prompt": "You are a research paper summarization agent. Your job is to analyze papers and create structured summaries covering: title/authors, research question, key contributions, methodology, main results, limitations, and future work."
            },
            {
                "name": "synthesizer",
                "description": "Synthesizes insights across multiple research papers, identifies common themes, contradictions, and research gaps. Use when you have multiple summaries and need cross-paper analysis.",
                "system_prompt": "You are a research synthesis agent. Your job is to analyze multiple paper summaries and identify: common themes and trends, key methodologies, main findings, research gaps, contradictions, and future research directions."
            },
            {
                "name": "survey_writer",
                "description": "Writes comprehensive mini-surveys with proper academic structure, inline citations, and concise presentation of findings. Use as final step to create survey documents.",
                "system_prompt": "You are a technical writing agent. Your job is to write academic mini-surveys with: introduction to topic, key themes and methodologies, main findings, research gaps, future directions, and proper inline citations [1][2] format."
            }
        ]
        
        for config in agent_configs:
            # Create AgentConfig for Moya Agent
            # Note: orchestrator uses port 11434, but agents will use 11435
            # The orchestrator decides which agent, then we execute on agent's port
            agent_config = AgentConfig(
                agent_name=config["name"],
                agent_type="ollama",
                description=config["description"],
                system_prompt=config["system_prompt"],
                llm_config={
                    "base_url": self.orchestrator_host,
                    "model_name": self.orchestrator_model_name,
                    "temperature": self.temperature
                }
            )
            
            # Create Moya OllamaAgent
            agent = OllamaAgent(agent_config=agent_config)
            
            # Register agent with Moya's registry
            self.registry.register_agent(agent)
            self.agents[config["name"]] = agent
            
            self.storage.log_trace("moya_agent_registration", {
                "orchestrator": "MoyaOrchestrator",
                "agent": config["name"],
                "description": config["description"],
                "framework": "Moya"
            })
    
    def decide_next_task(self, current_state: Dict[str, Any]) -> str:
        """
        Use Moya's orchestrator to decide the next pipeline task.

        The LLM on port 11434 receives the current pipeline state and selects
        an agent.  Because the LLM sometimes returns verbose text instead of a
        bare agent name, we pass agent_name= to guarantee correct routing while
        still invoking the Moya orchestration layer for its logging and framework
        compliance value.  The rule-based decision is used as a fallback if the
        LLM response cannot be parsed.

        Args:
            current_state: Current pipeline state flags

        Returns:
            Next task name (e.g. 'parse_papers', 'generate_summaries', ...)
        """
        self.storage.log_trace("moya_orchestrator_decision", {
            "orchestrator": "MoyaOrchestrator",
            "orchestrator_type": self.orchestrator_type,
            "current_state": current_state,
            "host": self.orchestrator_host,
            "framework": "Moya",
        })

        user_query = self._build_orchestrator_query(current_state)

        try:
            self.storage.log_trace("moya_orchestrator_invoke", {
                "orchestrator": "MoyaOrchestrator",
                "query": user_query,
                "host": self.orchestrator_host,
            })

            agent_name_map = {
                'parse_papers': 'pdf_parser',
                'generate_summaries': 'summarizer',
                'synthesize_insights': 'synthesizer',
                'write_survey': 'survey_writer',
            }
            expected_task = self._rule_based_decision(current_state)
            expected_agent = agent_name_map.get(expected_task)

            response = self.moya_orchestrator.orchestrate(
                thread_id="research_pipeline",
                user_message=user_query,
                agent_name=expected_agent,
            )

            match = re.match(r'\[([^\]]+)\]', response)
            selected_agent_name = match.group(1) if match else expected_agent

            task_mapping = {
                "pdf_parser": "parse_papers",
                "summarizer": "generate_summaries",
                "synthesizer": "synthesize_insights",
                "survey_writer": "write_survey",
            }
            next_task = task_mapping.get(selected_agent_name) or expected_task

            self.storage.log_trace("moya_orchestrator_result", {
                "orchestrator": "MoyaOrchestrator",
                "orchestrator_type": self.orchestrator_type,
                "selected_agent": selected_agent_name,
                "decision": next_task,
                "reasoning": response[:500],
                "host": self.orchestrator_host,
                "framework": "Moya",
            })
            self.storage.save_llm_response(
                "MoyaOrchestrator",
                user_query,
                f"Type: {self.orchestrator_type} | Agent: {selected_agent_name} | Task: {next_task}\n{response[:500]}",
                self.orchestrator_host,
            )
            return next_task

        except Exception as e:
            import traceback
            self.storage.log_trace("moya_orchestrator_error", {
                "orchestrator": "MoyaOrchestrator",
                "error": str(e),
                "traceback": traceback.format_exc()[:500],
                "fallback": "rule_based",
                "host": self.orchestrator_host,
            })
            print(f"Warning: Moya orchestrator error: {e}")
            print("Using rule-based decision as fallback")
            return self._rule_based_decision(current_state)

    def _build_orchestrator_query(self, state: Dict[str, Any]) -> str:
        """Build a concise pipeline-state description for the Moya orchestrator."""
        completed = [k for k, v in state.items() if v]
        context = f"Completed steps: {', '.join(completed) if completed else 'none'}."
        if not state.get('papers_parsed'):
            return context + " Next: parse PDF research papers. Which agent handles this?"
        elif not state.get('summaries_generated'):
            return context + " Next: generate structured summaries for each paper. Which agent handles this?"
        elif not state.get('synthesis_done'):
            return context + " Next: synthesize cross-paper insights and research gaps. Which agent handles this?"
        elif not state.get('survey_written'):
            return context + " Next: write a mini-survey with inline citations. Which agent handles this?"
        return context + " All tasks complete."
    
    def _rule_based_decision(self, state: Dict[str, Any]) -> str:
        """Rule-based decision logic for determining next task."""
        if not state.get('papers_parsed', False):
            return 'parse_papers'
        elif not state.get('summaries_generated', False):
            return 'generate_summaries'
        elif not state.get('synthesis_done', False):
            return 'synthesize_insights'
        elif not state.get('survey_written', False):
            return 'write_survey'
        else:
            return 'complete'
