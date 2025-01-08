from utils.config import load_config
import requests
import json
import logging
import sys
from typing import Dict, Any
from requests.exceptions import ConnectionError

class OllamaChat:
    def __init__(self, config_path: str = "config.toml"):
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        
        # Setup base URL
        self.base_url = f"{self.config['model']['base_url']}/api/chat"
        
        # Test server connection
        try:
            requests.get(self.config['model']['base_url'])
        except ConnectionError:
            self.logger.error("Ollama server is not running. Please start it with 'ollama serve'")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error initializing chat: {str(e)}")
            sys.exit(1)
        
        # Initialize conversation history
        self.history = []
        
    def _setup_logging(self):
        """Configure logging based on config settings"""
        logging.basicConfig(
            level=self.config['logging']['level'],
            filename=self.config['logging']['file'],
            format=self.config['logging']['format']
        )
        self.logger = logging.getLogger(__name__)
        
    def _make_request(self, messages: list) -> Dict[str, Any]:
        """Make a request to the Ollama API"""
        try:
            payload = {
                "model": self.config["model"]["name"],
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": self.config["model"]["temperature"],
                    "top_p": self.config["model"]["top_p"],
                    "num_predict": self.config["model"]["max_tokens"],
                }
            }
            
            for attempt in range(self.config["api"]["retry_attempts"]):
                try:
                    response = requests.post(
                        self.base_url,
                        json=payload,
                        timeout=self.config["api"]["request_timeout"]
                    )
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    if attempt == self.config["api"]["retry_attempts"] - 1:
                        raise
                    self.logger.warning(f"Request attempt {attempt + 1} failed: {str(e)}")
                    
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise
            
    def chat(self, user_input: str) -> str:
        """
        Send a message to the model and get a response
        
        Args:
            user_input (str): The user's input message
            
        Returns:
            str: The model's response
        """
        # Prepare messages including history
        messages = [{"role": "system", "content": self.config["system"]["prompt"]}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Get response from model
            response = self._make_request(messages)
            
            # Extract assistant's message
            assistant_message = response["message"]["content"]
            
            # Update conversation history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            self.logger.error(f"Chat failed: {str(e)}")
            return f"An error occurred: {str(e)}"
            
    def reset_conversation(self):
        """Clear the conversation history"""
        self.history = []
        self.logger.info("Conversation history reset")

def main():
    try:
        # Initialize the chat client
        chat_client = OllamaChat()
        
        print("Chat initialized. Type 'quit' to exit or 'reset' to clear history.")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'reset':
                    chat_client.reset_conversation()
                    print("Conversation history cleared.")
                    continue
                
                if user_input:
                    response = chat_client.chat(user_input)
                    print(f"\nAssistant: {response}")
            except KeyboardInterrupt:
                print("\nExiting chat...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Failed to initialize chat: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 