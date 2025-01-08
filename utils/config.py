import toml
import os
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str = "config.toml") -> Dict[str, Any]:
    """
    Load configuration from TOML file and set environment variables
    
    Args:
        config_path (str): Path to the config file
        
    Returns:
        dict: Configuration dictionary
    """
    try:
        # Load the config file
        config = toml.load(Path(config_path))
        
        # Set environment variables from config
        if 'environment' in config:
            for key, value in config['environment'].items():
                os.environ[key] = str(value)
        
        return config
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")

def get_model_config() -> Dict[str, Any]:
    """Get model-specific configuration"""
    config = load_config()
    return config.get('model', {})

def get_api_config() -> Dict[str, Any]:
    """Get API-specific configuration"""
    config = load_config()
    return config.get('api', {}) 