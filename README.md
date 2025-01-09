# Ollama Chatbot with Llama2

A modern chatbot implementation using Ollama's Llama2 model with both terminal and Pygame-based graphical user interfaces.

## Features

- Terminal-based chat interface
- Modern Pygame GUI with:
  - Real-time message streaming
  - Code block highlighting
  - Message bubbles
  - Smooth scrolling
  - Loading animations
- Configurable model settings via TOML
- Multi-threaded response handling

## Prerequisites

- Python 3.10 or higher
- Conda (for environment management)
- Ollama with Llama2 model installed

## Installation

1. Clone the repository:
```bash
git clone https://github.com/RyoK3N/Ollama-chatbot-lamma2
cd Ollama-chatbot-lamma2
```

2. Create and activate the conda environment:
```bash
chmod +x chatbot.sh
./chatbot.sh
```

## Usage

Run the chatbot script and choose your preferred interface:
```bash
./chatbot.sh
```

Select:
1. Terminal interface
2. Pygame GUI

## Configuration

Edit `config.toml` to customize:
- Model settings
- Server configuration
- Environment variables

## License

MIT License
