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
mkdir -p uploads

# Create .gitkeep files
touch papers/.gitkeep
touch uploads/.gitkeep

echo ""
echo "✅ Directory structure:"
echo "   papers/           - Place your PDF papers here"
echo "   uploads/          - Web app upload storage"
echo ""
echo "📝 Note: Run directories created automatically:"
echo "   run_YYYYMMDD_HHMMSS/        - CLI run outputs"
echo "   web_run_YYYYMMDD_HHMMSS/    - Web app outputs"
echo "   comparison_YYYYMMDD_HHMMSS/ - Comparison outputs"
echo ""

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not found"
    echo ""
    echo "Please install Ollama:"
    echo "  • Visit: https://ollama.ai"
    echo "  • After installation, run: ollama pull llama3.1"
    echo ""
else
    echo "✅ Ollama found"
    echo "Pulling llama3.1 model..."
    ollama pull llama3.1
fi

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Activate environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Add PDFs to papers/ folder"
echo ""
echo "3. Run interactive mode:"
echo "   python research_copilot_interactive.py --interactive"
echo ""
echo "4. Or run web app:"
echo "   streamlit run web_app.py"
echo ""
echo "5. Or process directly:"
echo "   python research_copilot_interactive.py ./papers"
echo ""
echo "📁 Each run creates a unique timestamped directory"
echo "=================================="
