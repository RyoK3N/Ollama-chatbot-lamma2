#!/bin/bash

# Initialize conda for shell
source ~/miniconda3/etc/profile.d/conda.sh || source ~/.conda/etc/profile.d/conda.sh

# Check if the environment exists
if ! conda env list | grep -q "chatbot"; then
    echo "Creating new conda environment 'chatbot'..."
    conda create -n chatbot python=3.10 -y
fi

# Activate the environment
conda activate chatbot

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start Ollama service if it's not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama service..."
    ollama serve &
    # Wait a bit for the service to start
    sleep 5
fi

# Pull the model if not already downloaded
if ! ollama list | grep -q "llama2"; then
    echo "Pulling llama2 model..."
    ollama pull llama2
fi

# Ask user which interface to use
echo "Choose interface:"
echo "1) Terminal"
echo "2) Pygame UI"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "Starting terminal interface..."
        python main.py
        ;;
    2)
        echo "Starting Pygame interface..."
        python pygame_ui.py
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac 