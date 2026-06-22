#!/bin/bash
# Setup script to run two Ollama instances.
#
# Two models are used:
#   ORCH_MODEL  — orchestrator routing only (port 11434): small/fast is fine
#   AGENT_MODEL — task agents: summarization, synthesis, survey (port 11435)
#
# Both models are pulled via the first instance. All Ollama instances share
# ~/.ollama/models/ so only one pull per model is needed.
#
# Ollama does not have a cross-version "latest" tag — each Llama release
# (llama3.1, llama3.2, ...) is a separate named model. Update these two
# variables when you want to upgrade.
ORCH_MODEL="llama3.2"   # 3B params, ~2GB RAM — fast routing decisions
AGENT_MODEL="llama3.1"  # 8B params, ~5GB RAM — quality summarization/synthesis

echo "Setting up two Ollama instances..."
echo "  Orchestrator model: $ORCH_MODEL (port 11434)"
echo "  Agent model:        $AGENT_MODEL (port 11435)"
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed"
    echo "Install from: https://ollama.com/download"
    exit 1
fi

# Kill any existing Ollama processes
echo "Stopping any existing Ollama instances..."
pkill -f "ollama serve" || true
sleep 2

# Start first instance (Orchestrator) on port 11434
echo "Starting Orchestrator Ollama on port 11434..."
OLLAMA_HOST=127.0.0.1:11434 ollama serve > ollama_orchestrator.log 2>&1 &
ORCH_PID=$!
echo "  PID: $ORCH_PID"
sleep 5

# Pull both models once via the first instance.
# Files land in ~/.ollama/models/ which is shared — no second pull needed.
echo "Pulling $ORCH_MODEL (orchestrator)..."
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$ORCH_MODEL"
echo "Pulling $AGENT_MODEL (agents)..."
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$AGENT_MODEL"

# Start second instance (Agents) on port 11435
echo ""
echo "Starting Agent Ollama on port 11435..."
OLLAMA_HOST=127.0.0.1:11435 ollama serve > ollama_agents.log 2>&1 &
AGENT_PID=$!
echo "  PID: $AGENT_PID"
sleep 5
# No pulls needed — second instance reads the same ~/.ollama/models/

# Verify both instances are running
echo ""
echo "Verifying instances..."
echo "Orchestrator (11434):"
OLLAMA_HOST=127.0.0.1:11434 ollama list

echo ""
echo "Agents (11435):"
OLLAMA_HOST=127.0.0.1:11435 ollama list

echo ""
echo "Setup complete!"
echo "  Orchestrator PID: $ORCH_PID (port 11434, model: $ORCH_MODEL)"
echo "  Agent PID:        $AGENT_PID (port 11435, model: $AGENT_MODEL)"
echo ""
echo "To stop both instances run: ./stop_ollama.sh"
echo "Log files: ollama_orchestrator.log, ollama_agents.log"
