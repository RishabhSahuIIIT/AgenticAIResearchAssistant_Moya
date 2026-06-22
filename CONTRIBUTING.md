# Contributing to Research Co-pilot

## Adding a new pipeline agent

1. **Create the agent file** in `research-copilot/agents/`.
   - If your agent calls an LLM, subclass `LLMBaseAgent`:
     ```python
     from agents.base_agent import LLMBaseAgent

     class MyAgent(LLMBaseAgent):
         def __init__(self, storage_manager, model_name="llama3.1", ollama_host="http://127.0.0.1:11435"):
             super().__init__("MyAgent", storage_manager, model_name, ollama_host)
     ```
   - If it does not call an LLM (e.g. a file processor), subclass `BaseAgent` instead.

2. **Add your prompt** to `research-copilot/prompts/templates.py` as a plain function that takes
   string arguments and returns a formatted string. Export it from `prompts/__init__.py`.

3. **Register the agent** in `research-copilot/main.py`:
   - Instantiate it in `ResearchCopilot.initialize_run()`.
   - Add a pipeline method (e.g. `run_my_step()`) that calls the agent and updates `pipeline_state`.
   - Call it in `run_full_pipeline()`.

4. **Register with the Moya orchestrator** in `orchestrator/moya_orchestrator.py`:
   - Add an entry to the `agent_configs` list in `_setup_moya_agents()`.
   - Add a mapping from your Moya agent name to the pipeline task name in `task_mapping`.

5. **Export the class** from `agents/__init__.py`.

## Error handling

- LLM calls raise `OllamaError` (from `tools.ollama_client`) on failure after 3 retries.
  Catch it in the pipeline method in `main.py` and log to `self.storage.log_trace("pipeline_error", ...)`.
- File I/O should go through `StorageManager` methods, not direct `open()` calls in agents.

## Configuration

All tuneable values live in `config/config.py`. The constructor validates them at startup —
add any new fields there and update `_validate()` accordingly.

## Running locally

```bash
# From research-copilot/
python main.py /path/to/pdfs       # automated pipeline
python main.py                     # interactive mode
```

Ensure two Ollama instances are running:
- Orchestrator on port 11434: `OLLAMA_HOST=0.0.0.0:11434 ollama serve`
- Agents on port 11435: `OLLAMA_HOST=0.0.0.0:11435 ollama serve`
