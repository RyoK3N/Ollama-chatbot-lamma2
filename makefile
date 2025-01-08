.PHONY: setup install start pull-model run clean

setup:
	conda create -n chatbot python=3.10 -y
	@echo "Environment created. Please run the following commands manually:"
	@echo "conda init"
	@echo "conda activate chatbot"
	@echo "make install"

install:
	brew install ollama
	pip install -r requirements.txt

start:
	ollama serve

pull-model:
	ollama pull llama2

run:
	python main.py

clean:
	rm -f chatbot.log
	rm -rf __pycache__
	rm -rf .cache
	rm -rf utils/__pycache__