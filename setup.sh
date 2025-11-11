#!/bin/bash

echo "=================================="
echo "Research Co-pilot Setup"
echo "=================================="

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p papers
mkdir -p summaries
mkdir -p summaries/parsed_content
mkdir -p uploads
mkdir -p comparison_summaries
mkdir -p web_summaries

# Create .gitkeep files
touch papers/.gitkeep
touch summaries/.gitkeep

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Please install from: https://ollama.ai"
    echo "After installation, run: ollama pull llama3.1"
else
    echo "Ollama found. Pulling llama3.1 model..."
    ollama pull llama3.1
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Activate environment: source venv/bin/activate"
echo "2. Add PDFs to papers/ folder"
echo "3. Run interactive mode: python research_copilot_interactive.py --interactive"
echo "4. Or run web app: streamlit run web_app.py"
echo ""
