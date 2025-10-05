"""
Utility to load and parse about page configuration from YAML
"""
import yaml
from pathlib import Path
from typing import Dict, Any
from flask import url_for


def _process_config_values(config: Any, context: Dict[str, Any] = None) -> Any:
    """
    Recursively process configuration values to replace placeholders
    """
    if context is None:
        context = {}
    
    if isinstance(config, dict):
        return {key: _process_config_values(value, context) for key, value in config.items()}
    elif isinstance(config, list):
        return [_process_config_values(item, context) for item in config]
    elif isinstance(config, str):
        # Replace common placeholders
        if config.startswith('url_for('):
            # Handle url_for() calls in config
            try:
                # Simple url_for extraction (extend as needed)
                endpoint = config.replace('url_for(', '').replace(')', '').replace("'", "").replace('"', '')
                return url_for(endpoint)
            except:
                return config
        return config
    else:
        return config


def load_about_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load about page configuration from YAML file
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "about.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Process any dynamic values
        return _process_config_values(config)
    
    except Exception as e:
        print(f"Error loading about config: {e}")
        return {}


def get_about_context() -> Dict[str, Any]:
    """
    Get about page context for template rendering
    """
    config = load_about_config()
    
    return {
        'about_config': config.get('about', {}),
        'about_icons': config.get('icons', {})
    }