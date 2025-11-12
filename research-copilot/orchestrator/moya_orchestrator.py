from typing import Dict, Any, List, Optional
from pathlib import Path
from tools.storage_tools import StorageManager
from tools.ollama_client import OrchestratorOllamaClient

# Import moya components - REQUIRED for this assignment
from moya.agents.agent import Agent, AgentConfig
from moya.agents.ollama_agent import OllamaAgent
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
        temperature: float = 0.7,
        seed: int = 42,
        orchestrator_host: str = "http://127.0.0.1:11434"
    ):
        self.storage = storage_manager
        self.model_name = model_name
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
            # MultiAgentOrchestrator can intelligently route based on query
            self.moya_orchestrator = MultiAgentOrchestrator(
                agent_registry=self.registry,
                model_name=model_name,
                base_url=orchestrator_host,
                temperature=temperature
            )
            self.orchestrator_type = "MultiAgent"
        except (TypeError, AttributeError) as e:
            # Fallback to SimpleOrchestrator
            self.moya_orchestrator = SimpleOrchestrator(
                agent_registry=self.registry,
                default_agent_name="pdf_parser"
            )
            self.orchestrator_type = "Simple"
        
        self.storage.log_trace("orchestrator_init", {
            "orchestrator": "MoyaOrchestrator",
            "orchestrator_type": self.orchestrator_type,
            "model": model_name,
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
                    "base_url": self.orchestrator_host,  # Orchestrator's URL for decision making
                    "model_name": self.model_name,
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
        Use Moya's orchestrator to decide next task based on current state.
        
        Args:
            current_state: Current pipeline state
            
        Returns:
            Next task to execute
        """
        self.storage.log_trace("moya_orchestrator_decision", {
            "orchestrator": "MoyaOrchestrator",
            "orchestrator_type": self.orchestrator_type,
            "current_state": current_state,
            "host": self.orchestrator_host,
            "framework": "Moya"
        })
        
        # Construct user query for Moya orchestrator
        user_query = self._build_orchestrator_query(current_state)
        
        try:
            # Use Moya's orchestrator to select appropriate agent
            self.storage.log_trace("moya_orchestrator_invoke", {
                "orchestrator": "MoyaOrchestrator",
                "query": user_query,
                "host": self.orchestrator_host
            })
            
            if self.orchestrator_type == "MultiAgent":
                # MultiAgentOrchestrator intelligently selects agent based on query
                result = self.moya_orchestrator.route(
                    user_message=user_query,
                    thread_id="research_pipeline"
                )
                selected_agent_name = result.get("agent_name", None)
                reasoning = result.get("reasoning", "Intelligent routing by MultiAgentOrchestrator")
            else:
                # SimpleOrchestrator with manual selection
                # We need to determine which agent based on state
                agent_name_map = {
                    'parse_papers': 'pdf_parser',
                    'generate_summaries': 'summarizer',
                    'synthesize_insights': 'synthesizer',
                    'write_survey': 'survey_writer'
                }
                task = self._rule_based_decision(current_state)
                selected_agent_name = agent_name_map.get(task)
                
                if selected_agent_name:
                    # Execute through Moya's orchestrator
                    response = self.moya_orchestrator.orchestrate(
                        thread_id="research_pipeline",
                        user_message=user_query,
                        agent_name=selected_agent_name
                    )
                    reasoning = f"SimpleOrchestrator routed to {selected_agent_name}: {response}"
                else:
                    reasoning = "Pipeline complete"
            
            # Map Moya agent name to pipeline task
            task_mapping = {
                "pdf_parser": "parse_papers",
                "summarizer": "generate_summaries",
                "synthesizer": "synthesize_insights",
                "survey_writer": "write_survey"
            }
            
            next_task = task_mapping.get(selected_agent_name, None)
            
            if not next_task:
                # All tasks complete
                next_task = self._rule_based_decision(current_state)
            
            self.storage.log_trace("moya_orchestrator_result", {
                "orchestrator": "MoyaOrchestrator",
                "orchestrator_type": self.orchestrator_type,
                "selected_agent": selected_agent_name,
                "decision": next_task,
                "reasoning": reasoning[:500] if reasoning else "",
                "host": self.orchestrator_host,
                "framework": "Moya"
            })
            
            # Save orchestrator decision
            self.storage.save_llm_response(
                "MoyaOrchestrator",
                user_query,
                f"Orchestrator Type: {self.orchestrator_type}\nSelected Agent: {selected_agent_name}\nTask: {next_task}\nReasoning: {reasoning[:500] if reasoning else 'N/A'}",
                self.orchestrator_host
            )
            
            return next_task
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            
            self.storage.log_trace("moya_orchestrator_error", {
                "orchestrator": "MoyaOrchestrator",
                "error": str(e),
                "traceback": error_trace[:500],
                "fallback": "rule_based",
                "host": self.orchestrator_host
            })
            print(f"Warning: Moya orchestrator error: {e}")
            print("Using rule-based decision as fallback")
            return self._rule_based_decision(current_state)
    
    def _build_orchestrator_query(self, state: Dict[str, Any]) -> str:
        """Build a natural language query for Moya's orchestrator."""
        
        # Build context about what's been done
        completed_steps = []
        if state.get('papers_parsed'):
            completed_steps.append("parsed PDF papers")
        if state.get('summaries_generated'):
            completed_steps.append("generated summaries")
        if state.get('synthesis_done'):
            completed_steps.append("synthesized insights")
        if state.get('survey_written'):
            completed_steps.append("written survey")
        
        context = f"Completed: {', '.join(completed_steps) if completed_steps else 'none'}. "
        
        # Determine next action needed
        if not state.get('papers_parsed', False):
            return context + "I need to parse PDF research papers from a folder and extract their content. Which agent should handle this?"
        elif not state.get('summaries_generated', False):
            return context + "I have parsed research papers and need to generate structured summaries for each paper. Which agent should handle this?"
        elif not state.get('synthesis_done', False):
            return context + "I have summaries of multiple papers and need to synthesize cross-paper insights and identify research gaps. Which agent should handle this?"
        elif not state.get('survey_written', False):
            return context + "I have paper summaries and synthesis, and need to write a comprehensive mini-survey with inline citations. Which agent should handle this?"
        else:
            return context + "All tasks are complete."
    
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
