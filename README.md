
# Research Co-pilot: Multi-Agent System for Research Paper Analysis

Originally built as part of the Topics in Software Engineering course at IIIT Hyderabad.

## 1. Overview

This project implements a multi-agent system for analyzing research papers using the **Moya framework** with **Ollama's Llama 3.1** model. The system operates with a unique dual-instance architecture where an orchestrator instance decides which tasks to execute, and a separate agent instance performs the actual work. This design enables true concurrent processing while maintaining clear separation of concerns.

The system parses PDF research papers, generates structured summaries, synthesizes cross-paper insights, identifies research gaps, and produces comprehensive mini-surveys with inline citations (≤800 words). All operations are fully logged with timestamps for complete observability and reproducibility.

**Role of orchestrator and task agent**: Two separate Ollama instances run on different ports (11434 for orchestrator, 11435 for agents), allowing the decision-making process to run independently of task execution, preventing blocking and timeout issues.

The implementation could be extended to instead setup separate ollama instances for each task agent as well, if it is required that tasks be executed concurrently. Proper synchronisation of input and outputs between agents will be required in this case.

## 2. Features

### Core Capabilities
- **PDF Parsing**: Extracts text, metadata, and structure from research papers using PyMuPDF
- **Structured Summarization**: Generates comprehensive summaries covering methodology, contributions, results, and limitations; uses map-reduce chunking for papers that exceed the context window
- **Cross-paper Synthesis**: Identifies themes, contradictions, research gaps, and future directions across multiple papers
- **Mini-survey Generation**: Creates academic surveys with proper citations and structure (≤800 words)
- **Run History**: Interactive menu option 7 shows all previous run folders with pipeline completion status
### Limitations
- **Sequential task execution**: Only one task agent runs at a time to avoid excess RAM usage on laptop hardware. Parallel summarization (e.g., with `ThreadPoolExecutor`) is feasible but not yet enabled — see the Performance section below.
- **No cross-run state resumption**: Each run creates a new output folder. Previous run outputs can be inspected via menu option 7. Files from a previous run can be manually copied into the new run folder to skip already-completed stages.
- **AMD iGPU acceleration**: Ollama has experimental ROCm support for AMD GPUs but integrated GPUs typically lack the VRAM for full GPU offload; the system runs on CPU by default.

### Technical Features
- **Moya-based Orchestration**: Uses Moya's agent registry and orchestrator for intelligent task routing
- **Dual Ollama Architecture**: Separate instances for orchestration (port 11434) and execution (port 11435)
- **Shared Model Storage**: Both instances use the same locally downloaded model files (pulled once via `setup_ollama.sh`)
- **Map-reduce Summarization**: Long papers are chunked, each chunk summarized independently, then combined — preserves context without truncation
- **Reference Section Stripping**: Bibliography sections are detected and removed before summarization to avoid wasting context tokens
- **Complete Observability**: Every operation logged to trace.jsonl with timestamps
- **Timestamped Outputs**: Each run creates a separate folder with all outputs timestamped
- **Output Description**: `OUTPUT_DESCRIPTION.md` generated in each run folder explaining every file type
- **Interactive Interface**: Terminal-based menu for step-by-step execution or full pipeline
- **Reproducibility**: Fixed seed and temperature settings stored in config for deterministic results
- **Error Handling**: Custom `OllamaError` exception with exponential backoff retry (3 attempts)

### Output Files Generated (per run folder)
- **`parsed_*.json` / `text_*.txt`**: Structured data and plain-text extract per paper
- **`parsing_summary_*.json`**: Overview of the parsing pass
- **`summary_*.json`**: Structured LLM summary per paper
- **`synthesis_*.json`**: Cross-paper insights and research gaps
- **`mini_survey_*.txt` / `mini_survey_*.json`**: Final academic survey (primary output)
- **`llm_response_*.json`**: All prompts and raw LLM replies for observability
- **`trace.jsonl`**: Complete execution trace in JSONL format
- **`config.json`**: Run configuration including model parameters
- **`OUTPUT_DESCRIPTION.md`**: Auto-generated guide to every file type in the folder

## 3. Assumptions 
Assuming that all tasks are performed in this sequence : parse -> summarize -> insights -> mini survey , using the outputs generated from immediate previous tasks.

### Environment Assumptions
- **Operating System**: Linux/Ubuntu (scripts designed for bash)
- **Python Version**: Python 3.8 or higher with venv support
- **Ollama Installation**: Ollama installed and accessible via command line
- **System Resources**: Minimum 16GB RAM recommended for running two Llama 3.1 instances
- **GPU (Optional)**: 8GB+ VRAM if using GPU acceleration but not mandatory
- **Disk Space**: Sufficient space for model storage (~5GB for Llama 3.1) per agent so at least 10 GB

### Input Assumptions
- **PDF Format**: Research papers must be in PDF format
- **Text Extractable**: PDFs should contain extractable text (not scanned images)
- **File Organization**: All papers in a single folder
- **Paper Count**: System designed for 5-6 papers (configurable)
- **Language**: Papers in English (or language supported by Llama 3.1)

### Model Assumptions
- **Model Name**: Uses "llama3.1" model (configurable in `config.py` — keep in sync with `setup_ollama.sh`)
- **Model Availability**: Llama 3.1 model downloaded locally via `setup_ollama.sh` (pulled once, shared between both Ollama instances)
- **Long Papers**: Papers exceeding 15,000 characters are split into overlapping chunks; each chunk is summarised then combined (map-reduce). Reference sections are stripped first.
- **Response Quality**: Assumes model can generate coherent summaries and analysis

### Moya Framework Assumptions
- **Source Installation**: Moya framework built from source (not pip installed)
- **Module Structure**: Uses Moya's agent, orchestrator, and registry modules
- **API Stability**: Assumes Moya API matches the structure used in imports
- **Ollama Integration**: Moya's OllamaAgent supports base_url configuration


## 4. Approach


### System Architecture
```text
┌─────────────────────────────────────────────────────┐
│              User Interface (main.py)               │
│         Interactive Menu / Command-line             │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│        Moya Orchestrator (port 11434)               │
│  - Analyzes pipeline state                          │
│  - Decides next task using LLM   ( ollama llama3.1) │
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
```
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

##  Design decisions 
- The system works by creating two ollama llama3.1 model instances on separate urls locally.
- I used ollama backend since it is free for use, my system can support its hardware requirements and it worked reasonably well when i directly prompted it to perform one of the functions of this project.
- Then while executing the code user can select the tasks to be performed by number in a cli interface.
- For parsing I used pyMupdf python library as agent tool. 
- Other agentic tasks are performed by the second ollama spawned instance since those tasks depend on the semantics of paper content and the intermediate outputs . 
- I implemented separate task agent ollama instance since the orchestrator while running on a single ollama instance was unable to delegate tasks to ollama since ollama was being used by it itself.
- Each input and output of agents (including orchestrator and task agent 's llm responses) is logged in separate files in the outputs /{run/current runtimestamp} directory and the decisions taken by the orchestrator are saved in trace.jsonl file per run. 
- Storing llm responses helped me identify and debug the ollama connection failures as well as see the flow of outputs and understand if it is consistent or not.
- For each tasks given to ollama based orchestrator and task agent , the prompts describing their role are coded into the respective python file and additional parameters required during runtime are taken as input in separate variables.
- The orchestrator is conveyed the different responsibilities for each agent at the beginning of the code run , and thereafter decides which agent to call based on input and context of recently completed task given by other agents's output.  Then it calls the required agent.




### Summary of Technology Stack
```
Frontend: Terminal-based interface (Python input/print)
Backend: Python 3.8+ with custom multi-agent system
Orchestration: Moya framework with dual Ollama instances
LLM: Llama 3.1 via Ollama
PDF Processing: PyMuPDF (fitz)
Storage: JSON files with timestamps
Logging: JSONL trace files
Environment: Linux/Ubuntu with Bash scripts
Model Management: Shared Ollama model directory
```


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
   ```bash
   # Download and install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Verify installation
   ollama --version
   ```

3. **Download Llama 3.1 Model** 
   ```bash
   ollama pull llama3.1
   ```


### Installation Steps

(all steps assuming virtual environment is active)

0. **Clone and Install Moya from Source (editable)**
   ```bash
   # Create and activate a virtual environment (named .venv by convention)
   python3 -m venv .venv
   source .venv/bin/activate

   # Clone Moya directly into ./moya — no intermediate staging folder or copy.
   # The editable install points at this directory at runtime, so it must persist.
   git clone git@github.com:montycloud/moya.git moya

   # Install moya with its ollama optional dependency (provides requests>=2.32.3).
   # (the pyproject.toml and the moya/ Python package live together inside moya/)
   pip install -e "moya/[ollama]"

   # Remove files not needed at runtime. The Python package and the editable
   # install metadata (moya/moya_ai.egg-info) stay; the rest is safe to delete.
   rm -rf moya/.git moya/docs moya/examples moya/mkdocs.yml
   ```


1. **Create Project Structure**
   ```
   mkdir -p research-copilot/{agents,tools,orchestrator,config,outputs}
   cd research-copilot
   ```


2. **Install Python Dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Add All Project Files**
   - Copy all the provided Python files into their respective directories
   - Place `setup_ollama.sh` and `stop_ollama.sh` in project root from the research copilot subfolder
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
5. Run full pipeline
6. Show current session state
7. Show all previous runs
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

# If not, reinstall (from the project root, not inside moya/)
pip install -e "moya/[ollama]"
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
├── OUTPUT_DESCRIPTION.md                            (guide to all file types)
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
```text
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
```
## 7. Software Engineering Practices

The codebase follows several SE principles that make it easier to maintain, extend, and debug.

### Abstraction and Inheritance
`BaseAgent` and `LLMBaseAgent` (in `agents/base_agent.py`) provide shared initialisation for all agents — name, storage handle, model name, and Ollama client. Adding a new agent requires only inheriting `LLMBaseAgent` and implementing the task method; no boilerplate is duplicated.

### Single Responsibility Principle
Each class has one job:
- `PDFParserAgent` — extract text from PDFs; no LLM calls
- `SummarizerAgent` / `SynthesizerAgent` / `SurveyWriterAgent` — one LLM task each
- `StorageManager` — all file I/O and trace logging
- `MoyaAgentOrchestrator` — pipeline routing only
- `Config` — configuration and validation only

### Separation of Concerns
LLM prompts are extracted to `prompts/templates.py` as pure functions. Changing a prompt does not require editing agent logic, and testing prompts in isolation is straightforward.

### Fail-Fast Configuration Validation
`Config._validate()` checks all configuration values (temperature range, non-empty model name, valid URLs) at startup before any network calls or file I/O, so misconfiguration surfaces immediately with a clear message.

### Custom Exceptions and Retry with Backoff
`OllamaError` is raised only when Ollama fails after all retry attempts. Retry uses exponential backoff (1 s, 2 s, 4 s) to handle transient connectivity issues without flooding the server. Pipeline code catches `OllamaError` at the stage boundary and logs it to `trace.jsonl`.

### Input Validation at Boundaries
`_validate_pdf_folder()` checks that the user-supplied path exists, is a directory, and contains at least one PDF before any parsing work begins — following the principle of validating at system entry points only.

### Type Hints and Docstrings
All public methods carry full type annotations and docstrings describing arguments, return values, and exceptions. This keeps the code self-documenting without comments that repeat what the code already says.

### Observability
Every agent call, LLM interaction, and pipeline decision is appended to `trace.jsonl` as a timestamped JSONL entry. Raw LLM prompts and responses are saved to `llm_response_*.json` files. `OUTPUT_DESCRIPTION.md` is generated automatically in each run folder so outputs are self-documenting.

### Reproducibility
`Config` stores `temperature` and `seed` which are passed to every LLM call. The same settings produce consistent outputs and are persisted in `config.json` alongside the run outputs.

---

## 8. Performance Optimisation Suggestions

The current pipeline processes papers sequentially on CPU. The following changes, ordered roughly from easiest to most impactful, can reduce wall-clock time significantly.

### 1. Parallel summarisation (threading)
The four `summarize_paper()` calls in `SummarizerAgent.summarize_all_papers()` are independent. Wrapping them with `concurrent.futures.ThreadPoolExecutor` parallelises the Ollama HTTP calls:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(self.summarize_paper, p): p for p in papers}
    for future in as_completed(futures):
        summaries.append(future.result())
```

With one Ollama instance per port this saturates the single model process, so the speedup is mainly from overlapping I/O and tokenisation. Running more Ollama instances (one per agent) would give true parallelism at the cost of additional RAM.

### 2. Smaller model for the orchestrator
The orchestrator only needs to route to one of four agent names — it does not need the full 8B model. Using `llama3.2` (3B, ~2 GB RAM) on port 11434 and keeping `llama3.1` (8B) on port 11435 cuts orchestrator response latency by roughly half without affecting output quality.

Change in `setup_ollama.sh`:
```bash
ORCH_MODEL="llama3.2"
AGENT_MODEL="llama3.1"
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$ORCH_MODEL"
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$AGENT_MODEL"   # shared dir, visible on 11435 too
```

Update `config.py` to expose `orchestrator_model_name` separately.

### 3. Quantised model (Q4 / Q5)
Ollama ships quantised variants for most models. Running `llama3.1:8b-instruct-q4_K_M` instead of the default `llama3.1` reduces memory by ~40% and inference time by ~30% with minor quality loss:

```bash
ollama pull llama3.1:8b-instruct-q4_K_M
```

Set `model_name = "llama3.1:8b-instruct-q4_K_M"` in `config.py`.

### 4. AMD GPU acceleration via ROCm
Ollama supports AMD GPUs through ROCm. If the device has a discrete AMD GPU (not integrated):

```bash
# Check ROCm device visibility
rocm-smi

# Start Ollama with GPU layers
OLLAMA_GPU_LAYERS=99 ollama serve
```

Integrated AMD GPUs share system RAM and typically do not benefit from this flag. For CPU-only systems, enabling AVX2/AVX-512 in the BIOS (if disabled) helps with llama.cpp throughput.

### 5. Skip re-parsing cached papers
If PDFs have not changed, re-parsing wastes time. `PDFParserAgent` could check for an existing `parsed_<name>_*.json` in the run folder (or a dedicated cache folder) before calling PyMuPDF again. This is especially useful when re-running summarisation after adjusting prompts.

---

## 9. Libraries and Technologies Used

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
- **Why chosen**: Purpose-built for multi-agent orchestration and agent coordination
- **Key components used**:
  - `moya.agents.agent.Agent`: Base agent class
  - `moya.agents.agent.AgentConfig`: Agent configuration
  - `moya.agents.ollama_agent.OllamaAgent`: Ollama-compatible agent
  - `moya.orchestrators.simple_orchestrator.SimpleOrchestrator`: Basic routing
  - `moya.orchestrators.multi_agent_orchestrator.MultiAgentOrchestrator`: Intelligent routing
  - `moya.registry.agent_registry.AgentRegistry`: Agent registration system
- **Usage in project**: Core orchestration layer that decides which agent handles each task
- **Repository**: https://github.com/montycloud/moya

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

**11. Llama 3.1 instance in ollama**
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

**reproducbility** : runs execute fine for given seed and temperature values in the config.json file 

Configuration parameters can be edited in the config.py file and (or the default parameters in orchestrator object constructor )under research-copilot folder.

**observability**: all decisions , llm outputs, pdf parsed data are logged in outputs directory.


### Logging and Observability

**15. Custom Logging (trace.jsonl)**
- **Format**: JSON Lines (JSONL)
- **Purpose**: Complete execution trace
- **Content**: Every agent call, tool call, LLM interaction, and decision
- **Why JSONL**: Easy to parse, append-only, human-readable


### Why This Stack?

- **Local-first**: No external API dependencies or costs
- **Reproducible**: Fixed seeds and temperature, all logs saved
- **Scalable**: Dual-instance architecture prevents blocking
- **Observable**: Complete trace of all operations
- **Flexible**: Easy to swap models or add new agents
- **Educational**: Clear separation of concerns for learning

---
References


[Ollama ](https://ollama.com/)

[pymupdf](https://pypi.org/project/PyMuPDF/)

[moya-ai github repo](https://github.com/montycloud/moya/tree/main)

[moya-ai python package](https://pypi.org/project/moya-ai/)
