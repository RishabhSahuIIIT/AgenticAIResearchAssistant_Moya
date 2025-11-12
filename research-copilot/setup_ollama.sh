#!/bin/bash
# Setup script to run two Ollama instances on different ports

echo "Setting up two Ollama instances..."
echo "  - Orchestrator: port 11434"
echo "  - Agents: port 11435"

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Error: Ollama is not installed"
    echo "Install from: https://ollama.com/download"
    exit 1
fi

# Pull the model if not already present
echo "Ensuring llama3.1 model is available..."
ollama pull llama3.1

# Kill any existing Ollama processes
echo "Stopping any existing Ollama instances..."
pkill -f "ollama serve" || true
sleep 2

# Start first Ollama instance (Orchestrator) on port 11434
echo "Starting Orchestrator Ollama on port 11434..."
OLLAMA_HOST=127.0.0.1:11434 ollama serve > ollama_orchestrator.log 2>&1 &
ORCH_PID=$!
echo "  PID: $ORCH_PID"

# Wait for first instance to start
sleep 3

# Start second Ollama instance (Agents) on port 11435
echo "Starting Agent Ollama on port 11435..."
OLLAMA_HOST=127.0.0.1:11435 ollama serve > ollama_agents.log 2>&1 &
AGENT_PID=$!
echo "  PID: $AGENT_PID"

# Wait for second instance to start
sleep 3

# Verify both instances are running
echo ""
echo "Verifying instances..."
curl -s http://127.0.0.1:11434/api/tags > /dev/null && echo "  ✓ Orchestrator (11434) is running" || echo "  ✗ Orchestrator failed"
curl -s http://127.0.0.1:11435/api/tags > /dev/null && echo "  ✓ Agents (11435) is running" || echo "  ✗ Agents failed"

echo ""
echo "Setup complete!"
echo "Orchestrator PID: $ORCH_PID (port 11434)"
echo "Agent PID: $AGENT_PID (port 11435)"
echo ""
echo "To stop both instances:"
echo "  kill $ORCH_PID $AGENT_PID"
echo ""
echo "Log files:"
echo "  ollama_orchestrator.log"
echo "  ollama_agents.log"
