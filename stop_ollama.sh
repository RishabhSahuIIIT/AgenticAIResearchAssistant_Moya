#!/bin/bash
# Stop all Ollama instances

echo "Stopping all Ollama instances..."
pkill -f "ollama serve"
sleep 2
echo "✓ All Ollama instances stopped"
