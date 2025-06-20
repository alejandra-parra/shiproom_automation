"""
Configuration loader for the Jellyfish Status Report Generator
"""

import yaml
from typing import Dict
from pathlib import Path

def load_config(config_path: str) -> Dict:
    """Load configuration from a YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        raise 