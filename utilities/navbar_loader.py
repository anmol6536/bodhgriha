"""
Utility to load and parse navbar configuration from YAML
"""
import yaml
from pathlib import Path
from typing import Dict, Any
from flask import url_for


def _process_config_values(config: Any, context: Dict[str, Any] = None) -> Any:
    """
    Recursively process configuration values to handle special cases like url_for
    
    Args:
        config: Configuration value (dict, list, or primitive)
        context: Context dictionary with Flask app config, current_user, etc.
    
    Returns:
        Processed configuration
    """
    if context is None:
        context = {}
    
    if isinstance(config, dict):
        return {key: _process_config_values(value, context) for key, value in config.items()}
    elif isinstance(config, list):
        return [_process_config_values(item, context) for item in config]
    elif isinstance(config, str):
        # Don't process Jinja2 template strings that reference current_user or config
        # These will be rendered in the template
        return config
    else:
        return config


def load_navbar_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load navbar configuration from YAML file
    
    Args:
        config_path: Path to the YAML config file. If None, uses default location.
    
    Returns:
        Dictionary containing navbar configuration
    """
    if config_path is None:
        # Default path relative to project root
        base_dir = Path(__file__).parent.parent
        config_path = base_dir / "config" / "navbar.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Navbar config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def get_navbar_context() -> Dict[str, Any]:
    """
    Get navbar configuration for template context
    
    Returns:
        Dictionary to be passed to template context
    """
    config = load_navbar_config()
    return {
        'navbar_config': config.get('navbar', {}),
        'navbar_icons': config.get('icons', {})
    }
