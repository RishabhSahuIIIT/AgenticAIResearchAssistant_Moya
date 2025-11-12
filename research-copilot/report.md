```
# Research Co-pilot: Multi-Agent System for Research Paper Analysis

## PROJECT REPORT

## 1. Overview

This project implements a multi-agent system for analyzing research papers using the **Moya framework** with **Ollama's Llama 3.1** model. The system operates with a unique dual-instance architecture where an orchestrator instance decides which tasks to execute, and a separate agent instance performs the actual work. This design enables true concurrent processing while maintaining clear separation of concerns.

The system parses PDF research papers, generates structured summaries, synthesizes cross-paper insights, identifies research gaps, and produces comprehensive mini-surveys with inline citations (≤800 words). All operations are fully logged with timestamps for complete observability and reproducibility.

**Key Innovation**: Two separate Ollama instances run on different ports (11434 for orchestrator, 11435 for agents), allowing the decision-making process to run independently of task execution, preventing blocking and timeout issues.

## 2. Features

### Core Capabilities
- **PDF Parsing**: Extracts text, metadata, and structure from research papers using PyMuPDF
- **Structured Summarization**: Generates comprehensive summaries covering methodology, contributions, results, and limitations
- **Cross-paper Synthesis**: Identifies themes, contradictions, research gaps, and future directions across multiple papers
- **Mini-survey Generation**: Creates academic surveys with proper citations and structure (≤800 words)

### Technical Features
- **Moya-based Orchestration**: Uses Moya's agent registry and orchestrator for intelligent task routing
- **Dual Ollama Architecture**: Separate instances for orchestration (port 11434) and execution (port 11435)
- **Shared Model Storage**: Both instances use the same locally downloaded model files to save disk space
- **Complete Observability**: Every operation logged to trace.jsonl with timestamps
- **Timestamped Outputs**: Each run creates a separate folder with all outputs timestamped
- **Interactive Interface**: Terminal-based menu for step-by-step execution or full pipeline
- **Reproducibility**: Fixed seed and temperature settings stored in config for deterministic results
- **Error Handling**: Comprehensive error logging with fallback mechanisms

### Output Files Generated
- **Parsed papers**: JSON and TXT formats for each paper
- **Parsing summary**: Overview of all parsed papers
- **Individual summaries**: Structured JSON summaries per paper
- **Synthesis report**: Cross-paper insights and gaps
- **Mini-survey**: Academic survey with citations
- **LLM responses**: All prompts and responses saved with host information
- **Trace log**: Complete execution trace in JSONL format
- **Configuration**: Run configuration including model parameters

## 3. Assumptions

### Environment Assumptions
- **Operating System**: Linux/Ubuntu (scripts designed for bash)
- **Python Version**: Python 3.8 or higher with venv support
- **Ollama Installation**: Ollama installed and accessible via command line
- **System Resources**: Minimum 16GB RAM recommended for running two Llama 3.1 instances
- **GPU (Optional)**: 8GB+ VRAM if using GPU acceleration
- **Disk Space**: Sufficient space for model storage (~5GB for Llama 3.1)

### Input Assumptions
- **PDF Format**: Research papers must be in PDF format
- **Text Extractable**: PDFs should contain extractable text (not scanned images)
- **File Organization**: All papers in a single folder
- **Paper Count**: System designed for 5-6 papers (configurable)
- **Language**: Papers in English (or language supported by Llama 3.1)

### Model Assumptions
- **Model Name**: Uses "llama3.1" model (configurable in config.py)
- **Model Availability**: Llama 3.1 model downloaded locally
- **Context Limits**: Papers truncated to 15,000 characters if too long
- **Response Quality**: Assumes model can generate coherent summaries and analysis

### Moya Framework Assumptions
- **Source Installation**: Moya framework built from source (not pip installed)
- **Module Structure**: Uses Moya's agent, orchestrator, and registry modules
- **API Stability**: Assumes Moya API matches the structure used in imports
- **Ollama Integration**: Moya's OllamaAgent supports base_url configuration

## 4. How It Works

### System Architecture

┌─────────────────────────────────────────────────────┐
│              User Interface (main.py)               │
│         Interactive Menu / Command-line             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│        Moya Orchestrator (port 11434)               │
│  - Analyzes pipeline state                          │
│  - Decides next task using LLM                      │
│  - Uses Moya's agent registry                       │
└────────────────────┬────────────────────────────────┘
                     │ Task Decision
                     ▼
┌─────────────────────────────────────────────────────┐
│              Agent Execution Layer                  │
│                 (port 11435)                        │
├─────────────────────────────────────────────────────┤
│  PDFParserAgent → Parse papers (no LLM)             │
│  SummarizerAgent → Generate summaries (LLM)         │
│  SynthesizerAgent → Find insights (LLM)             │
│  SurveyWriterAgent → Create survey (LLM)            │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│         Storage & Logging (trace.jsonl)             │
│  - Timestamped outputs in separate folders          │
│  - Complete execution trace                         │
│  - All LLM interactions saved                       │
└─────────────────────────────────────────────────────┘

### Execution Flow

1. **Initialization**
   - Create timestamped run folder (e.g., `run_20251113_025500`)
   - Initialize Moya orchestrator with agent registry
   - Register all agents (pdf_parser, summarizer, synthesizer, survey_writer)
   - Configure both Ollama instances with shared model directory
   - Save configuration to config.json

2. **Task 1: Parse Papers**
   - Orchestrator analyzes state: "papers not parsed"
   - Decides: "use pdf_parser agent"
   - PDFParserAgent scans folder for PDFs
   - Extracts text using PyMuPDF
   - Saves parsed data (JSON + TXT) with timestamps
   - Saves parsing summary
   - Updates state: papers_parsed = True

3. **Task 2: Generate Summaries**
   - Orchestrator analyzes state: "papers parsed, no summaries"
   - Decides: "use summarizer agent"
   - SummarizerAgent iterates through parsed papers
   - For each paper: sends text + prompt to Ollama (port 11435)
   - Generates structured summary (7 sections)
   - Saves summary JSON and LLM response
   - Updates state: summaries_generated = True

4. **Task 3: Synthesize Insights**
   - Orchestrator analyzes state: "summaries exist, no synthesis"
   - Decides: "use synthesizer agent"
   - SynthesizerAgent combines all summaries
   - Sends combined summaries + prompt to Ollama (port 11435)
   - Identifies themes, gaps, contradictions
   - Saves synthesis JSON and LLM response
   - Updates state: synthesis_done = True

5. **Task 4: Write Mini-Survey**
   - Orchestrator analyzes state: "synthesis done, no survey"
   - Decides: "use survey_writer agent"
   - SurveyWriterAgent combines summaries + synthesis
   - Sends synthesis + prompt (with 800-word limit) to Ollama (port 11435)
   - Generates academic survey with inline citations
   - Adds references section
   - Saves survey TXT and JSON with LLM response
   - Updates state: survey_written = True

6. **Completion**
   - All tasks completed
   - Orchestrator returns "complete"
   - Display summary to user
   - All outputs in timestamped folder

### Moya Framework Integration

The system uses Moya's core components:

- **AgentRegistry**: Registers all agents with descriptions and capabilities
- **AgentConfig**: Configures each agent with LLM settings and system prompts
- **OllamaAgent**: Creates Moya-compatible agents using Ollama backend
- **SimpleOrchestrator/MultiAgentOrchestrator**: Routes tasks to appropriate agents
- **orchestrate() method**: Executes tasks through Moya's orchestration layer

Each orchestration decision is logged with reasoning, and Moya's agent selection mechanism determines which agent handles each task based on the current pipeline state.

## 5. Setup and Execution Steps

### Prerequisites

1. **System Requirements**
   - Linux/Ubuntu operating system
   - Python 3.8 or higher
   - 16GB+ RAM (for dual Ollama instances)
   - 10GB+ disk space
   - Bash shell for scripts

2. **Install Ollama**
   ```
   # Download and install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Verify installation
   ollama --version
   ```

3. **Download Llama 3.1 Model** (one-time download)
   ```
   ollama pull llama3.1
   ```

4. **Clone and Install Moya from Source**
   ```
   # Clone Moya repository
   git clone https://github.com/montycloyd/moya.git
   
   # Install in development mode
   cd moya
   pip install -e .
   cd ..
   ```

### Installation Steps

1. **Create Project Structure**
   ```
   mkdir -p research-copilot/{agents,tools,orchestrator,config,outputs}
   cd research-copilot
   ```

2. **Create Virtual Environment**
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**
   ```
   pip install pymupdf ollama python-dotenv
   ```

4. **Add All Project Files**
   - Copy all the provided Python files into their respective directories
   - Place `setup_ollama.sh` and `stop_ollama.sh` in project root
   - Make scripts executable:
   ```
   chmod +x setup_ollama.sh stop_ollama.sh
   ```

5. **Prepare Research Papers**
   ```
   mkdir papers
   # Copy 5-6 PDF research papers into this folder
   ```

### Execution Steps

**Step 1: Start Ollama Instances**
```
./setup_ollama.sh
```

This will:
- Start orchestrator on port 11434
- Start agents on port 11435
- Configure shared model directory
- Verify both instances can access llama3.1

**Step 2: Run the Application**

**Option A: Interactive Mode**
```
python main.py
```
Then follow the menu:
1. Parse papers from folder (enter: `papers`)
2. Generate summaries
3. Synthesize insights
4. Write mini-survey
5. View state
0. Exit

**Option B: Full Pipeline (Command-line)**
```
python main.py papers/
```

This runs all steps automatically.

**Step 3: View Results**
```
# Find your run folder
ls -lt outputs/

# View the latest run
cd outputs/run_YYYYMMDD_HHMMSS/

# Check what was generated
ls -lh

# View trace log
tail -f trace.jsonl

# View mini-survey
cat mini_survey_*.txt
```

**Step 4: Stop Ollama Instances**
```
./stop_ollama.sh
```

### Troubleshooting

**Model not found error:**
```
# Ensure model is pulled for shared directory
export OLLAMA_MODELS="${HOME}/.ollama/models"
ollama pull llama3.1

# Verify both instances see it
OLLAMA_HOST=127.0.0.1:11434 ollama list
OLLAMA_HOST=127.0.0.1:11435 ollama list
```

**Port already in use:**
```
# Check what's using the ports
lsof -i :11434
lsof -i :11435

# Kill existing processes
pkill -f "ollama serve"
```

**Moya import errors:**
```
# Verify Moya is installed
python -c "from moya.agents.agent import Agent; print('Moya OK')"

# If not, reinstall
cd /path/to/moya
pip install -e .
```

**Out of memory:**
- Reduce number of papers processed
- Use a smaller model (e.g., llama3.2)
- Increase swap space
- Close other applications

## 6. Sample Input and Output

### Sample Input Structure

**papers/ folder:**
```
papers/
├── paper1_agile_story_points.pdf
├── paper2_software_estimation.pdf
├── paper3_development_effort.pdf
├── paper4_agile_metrics.pdf
└── paper5_project_management.pdf
```

### Sample Output Structure

**outputs/run_20251113_025500/ folder:**
```
outputs/run_20251113_025500/
├── config.json                                      (266 bytes)
├── trace.jsonl                                     (15.2 KB)
├── parsed_paper1_agile_story_points_20251113_025501.json    (128 KB)
├── text_paper1_agile_story_points_20251113_025501.txt       (89 KB)
├── parsed_paper2_software_estimation_20251113_025502.json   (156 KB)
├── text_paper2_software_estimation_20251113_025502.txt      (112 KB)
├── parsed_paper3_development_effort_20251113_025503.json    (143 KB)
├── text_paper3_development_effort_20251113_025503.txt       (98 KB)
├── parsed_paper4_agile_metrics_20251113_025504.json         (135 KB)
├── text_paper4_agile_metrics_20251113_025504.txt            (95 KB)
├── parsed_paper5_project_management_20251113_025505.json    (149 KB)
├── text_paper5_project_management_20251113_025505.txt       (105 KB)
├── parsing_summary_20251113_025506.json             (2.3 KB)
├── summary_paper1_agile_story_points_20251113_025520.json   (4.5 KB)
├── summary_paper2_software_estimation_20251113_025535.json  (4.8 KB)
├── summary_paper3_development_effort_20251113_025550.json   (4.2 KB)
├── summary_paper4_agile_metrics_20251113_025605.json        (4.6 KB)
├── summary_paper5_project_management_20251113_025620.json   (4.4 KB)
├── synthesis_20251113_025640.json                   (6.7 KB)
├── mini_survey_20251113_025710.txt                  (5.2 KB)
├── mini_survey_20251113_025710.json                 (6.1 KB)
├── llm_response_Orchestrator_20251113_025500_123456.json    (1.2 KB)
├── llm_response_SummarizerAgent_20251113_025520_234567.json (3.8 KB)
├── llm_response_SummarizerAgent_20251113_025535_345678.json (3.9 KB)
├── llm_response_SummarizerAgent_20251113_025550_456789.json (3.7 KB)
├── llm_response_SummarizerAgent_20251113_025605_567890.json (3.8 KB)
├── llm_response_SummarizerAgent_20251113_025620_678901.json (3.8 KB)
├── llm_response_SynthesizerAgent_20251113_025640_789012.json (5.4 KB)
└── llm_response_SurveyWriterAgent_20251113_025710_890123.json (6.2 KB)
```

### Sample config.json
```
{
  "timestamp": "20251113_025500",
  "model_name": "llama3.1",
  "model_backend": "ollama",
  "temperature": 0.7,
  "seed": 42,
  "max_papers": 6,
  "survey_word_limit": 800,
  "orchestrator_host": "http://127.0.0.1:11434",
  "agent_host": "http://127.0.0.1:11435"
}
```

### Sample trace.jsonl (excerpt)
```
{"timestamp": "2025-11-13T02:55:00.123456", "event_type": "system_init", "data": {"run_folder": "outputs/run_20251113_025500", "config": {"model": "llama3.1", "temperature": 0.7, "seed": 42}}}
{"timestamp": "2025-11-13T02:55:00.234567", "event_type": "orchestrator_init", "data": {"orchestrator": "MoyaOrchestrator", "model": "llama3.1", "host": "http://127.0.0.1:11434", "framework": "Moya"}}
{"timestamp": "2025-11-13T02:55:00.345678", "event_type": "moya_agent_registration", "data": {"orchestrator": "MoyaOrchestrator", "agent": "pdf_parser", "description": "Parses PDF research papers", "framework": "Moya"}}
{"timestamp": "2025-11-13T02:55:01.456789", "event_type": "agent_call", "data": {"agent": "PDFParserAgent", "action": "parse_papers", "num_files": 5}}
{"timestamp": "2025-11-13T02:55:20.567890", "event_type": "llm_call", "data": {"agent": "SummarizerAgent", "model": "llama3.1", "paper": "paper1_agile_story_points.pdf", "ollama_host": "http://127.0.0.1:11435"}}
```

### Sample Mini-Survey Output (mini_survey_20251113_025710.txt)

Agile Story Points and Development Effort: A Mini-Survey

Introduction

In agile software development, story points serve as a widely adopted metric for estimating task complexity and development effort [1][2]. This survey examines recent research on the relationship between story points and actual development effort, exploring methodologies, key findings, and identifying gaps in current understanding.

Methodologies and Approaches

The reviewed papers employ diverse methodological approaches to investigate story point accuracy. Statistical analysis of historical project data forms the foundation of most studies [1][3], with researchers examining correlations between estimated story points and actual hours worked. Machine learning techniques have emerged as promising tools for improving estimation accuracy [4], while qualitative studies explore team dynamics and estimation practices [5].

Key Findings

Research consistently demonstrates a moderate positive correlation between story points and development effort, though significant variance exists across projects and teams [1][2][3]. Context factors such as team experience, project complexity, and organizational culture significantly influence estimation accuracy [2][5]. Studies indicate that story points perform better as relative measures rather than absolute predictors of effort [3][4].

Research Gaps and Limitations

Despite growing interest, several gaps remain. Limited longitudinal studies prevent understanding how story point accuracy evolves over project lifecycles. Few papers address the impact of distributed teams on estimation consistency [5]. The influence of technical debt on story point reliability remains underexplored [2][3]. Additionally, most research focuses on single organizations, limiting generalizability across industry contexts.

Future Directions

Future research should investigate adaptive estimation techniques that account for team maturity and project evolution. Cross-organizational studies would strengthen external validity. Integration of automated tools with human judgment represents a promising avenue for improving estimation accuracy [4]. Research examining story points in scaled agile frameworks and distributed environments is particularly needed.

## References
[1] paper1_agile_story_points.pdf: On the Relationship Between Story Points and Development Effort in Agile Open-Source Software
[2] paper2_software_estimation.pdf: Software Effort Estimation Using Agile Metrics
[3] paper3_development_effort.pdf: Predicting Development Effort from Story Points
[4] paper4_agile_metrics.pdf: Machine Learning Approaches to Agile Estimation
[5] paper5_project_management.pdf: Team Dynamics in Agile Story Point Estimation

## 7. Libraries and Technologies Used

### Core Python Libraries

**1. PyMuPDF (fitz) - v1.23.0+**
- **Purpose**: PDF text extraction and parsing
- **Why chosen**: High-performance Python library for PDF manipulation
- **Key features**: 
  - Extracts text with layout preservation
  - Retrieves PDF metadata (title, author, subject)
  - Page-by-page text extraction
  - Handles complex PDF structures
- **Usage in project**: PDFParserAgent uses PyMuPDF to extract all text content from research papers
- **Documentation**: https://pymupdf.readthedocs.io/

**2. Ollama Python Client - v0.1.0+**
- **Purpose**: Interface with Ollama LLM server
- **Why chosen**: Official Python library for Ollama with custom host support
- **Key features**:
  - HTTP client for Ollama API
  - Support for custom base URLs (multi-instance setup)
  - Generate and chat endpoints
  - Timeout configuration
- **Usage in project**: 
  - OrchestratorOllamaClient connects to port 11434
  - AgentOllamaClient connects to port 11435
  - All LLM interactions go through these clients
- **Documentation**: https://github.com/ollama/ollama-python

**3. Moya Framework (from source)**
- **Purpose**: Multi-agent orchestration framework
- **Why chosen**: Required by assignment, designed for agent coordination
- **Key components used**:
  - `moya.agents.agent.Agent`: Base agent class
  - `moya.agents.agent.AgentConfig`: Agent configuration
  - `moya.agents.ollama_agent.OllamaAgent`: Ollama-compatible agent
  - `moya.orchestrators.simple_orchestrator.SimpleOrchestrator`: Basic routing
  - `moya.orchestrators.multi_agent_orchestrator.MultiAgentOrchestrator`: Intelligent routing
  - `moya.registry.agent_registry.AgentRegistry`: Agent registration system
- **Usage in project**: Core orchestration layer that decides which agent handles each task
- **Repository**: https://github.com/montycloyd/moya

**4. python-dotenv - v1.0.0+**
- **Purpose**: Environment variable management
- **Why chosen**: Clean way to manage configuration
- **Key features**: Loads .env files into environment
- **Usage in project**: Could be used for storing Ollama hosts and API keys
- **Documentation**: https://pypi.org/project/python-dotenv/

### Supporting Python Standard Libraries

**5. pathlib**
- **Purpose**: Object-oriented filesystem paths
- **Usage**: File and directory manipulation throughout the project

**6. json**
- **Purpose**: JSON serialization/deserialization
- **Usage**: Saving all outputs (summaries, synthesis, configs, traces)

**7. datetime**
- **Purpose**: Timestamp generation
- **Usage**: Creating timestamped filenames and log entries

**8. typing**
- **Purpose**: Type hints
- **Usage**: Function signatures for better code documentation

**9. subprocess**
- **Purpose**: Execute external commands (optional fallback)
- **Usage**: Could be used as fallback for Ollama calls

### External Services

**10. Ollama**
- **Version**: Latest stable
- **Purpose**: Run Llama 3.1 LLM locally
- **Architecture**: Two separate instances on ports 11434 and 11435
- **Model storage**: Shared directory at ~/.ollama/models
- **Why chosen**: 
  - Local deployment (no API costs)
  - Supports concurrent instances
  - Model sharing between instances
  - Good performance with Llama 3.1
- **Website**: https://ollama.com

**11. Llama 3.1**
- **Developer**: Meta AI
- **Purpose**: Large language model for text generation
- **Why chosen**:
  - Strong reasoning capabilities
  - Good for research paper analysis
  - Moderate resource requirements
  - Widely supported
- **Model size**: ~5GB download

### Development Tools

**12. Python Virtual Environment (venv)**
- **Purpose**: Isolated Python environment
- **Why used**: Dependency isolation and reproducibility

**13. Bash Scripts**
- **Purpose**: Setup and teardown automation
- **Files**: setup_ollama.sh, stop_ollama.sh
- **Why used**: Simplify multi-instance Ollama management

### Project Structure Libraries (Standard Python)

**14. __init__.py files**
- **Purpose**: Package initialization
- **Usage**: Makes directories importable as Python packages

### Logging and Observability

**15. Custom Logging (trace.jsonl)**
- **Format**: JSON Lines (JSONL)
- **Purpose**: Complete execution trace
- **Content**: Every agent call, tool call, LLM interaction, and decision
- **Why JSONL**: Easy to parse, append-only, human-readable

### Summary of Technology Stack

Frontend: Terminal-based interface (Python input/print)
Backend: Python 3.8+ with custom multi-agent system
Orchestration: Moya framework with dual Ollama instances
LLM: Llama 3.1 via Ollama
PDF Processing: PyMuPDF (fitz)
Storage: JSON files with timestamps
Logging: JSONL trace files
Environment: Linux/Ubuntu with Bash scripts
Model Management: Shared Ollama model directory

### Why This Stack?

- **Local-first**: No external API dependencies or costs
- **Reproducible**: Fixed seeds and temperature, all logs saved
- **Scalable**: Dual-instance architecture prevents blocking
- **Observable**: Complete trace of all operations
- **Flexible**: Easy to swap models or add new agents
- **Educational**: Clear separation of concerns for learning

---

**Assignment Compliance Checklist:**
✓ Uses Moya framework for orchestration
✓ Integrates Ollama with Llama 3.1
✓ Dual Ollama instances (orchestrator + agents)
✓ Parses 5-6 research papers
✓ Generates structured summaries
✓ Synthesizes cross-paper insights
✓ Creates mini-survey ≤800 words with citations
✓ Timestamped outputs in separate folders
✓ Complete observability via trace.jsonl
✓ Reproducible with fixed seed/temperature
✓ Built with Moya from source
✓ No hard-coded answers
```

[1](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-and-highlighting-code-blocks)
[2](https://www.markdownguide.org/extended-syntax/)
[3](https://www.codecademy.com/resources/docs/markdown/code-blocks)
[4](https://www.markdownguide.org/basic-syntax/)
[5](https://www.glukhov.org/post/2025/07/markdown-codeblocks/)
[6](https://www.youtube.com/watch?v=IG9_EM5cw3U)
[7](https://www.jetbrains.com/help/hub/markdown-syntax.html)
[8](https://learn.microsoft.com/en-us/azure/devops/project/wiki/markdown-guidance?view=azure-devops)
[9](https://elischei.com/syntax-highlighting-in-markdown-code-blocks/)
[10](https://confluence.atlassian.com/bitbucketserver/markdown-syntax-guide-776639995.html)
