# Destination: src/catpic/config.py

"""
Configuration management for catpic.

Uses a single JSON environment variable (CATPIC_CONFIG) with flattened structure.
Keys use spaces for readability: "aspect 2x4" not "aspect_2x4"
"""

import os
import json
import sys
from typing import Optional, Dict, Any
from difflib import get_close_matches


# Canonical configuration keys with descriptions and types
CONFIG_SCHEMA = {
    "protocol": {
        "description": "Display protocol",
        "type": str,
        "valid": ["auto", "glyxel", "glyxel_only", "kitty", "sixel"],
        "default": "auto",
    },
    "basis": {
        "description": "Encoding quality",
        "type": str,
        "valid": ["1,2", "2,2", "2,3", "2,4"],
        "default": "2,2",
    },
    "aspect base": {
        "description": "Base character aspect ratio",
        "type": float,
        "default": 2.0,
    },
    "aspect 1x2": {
        "description": "Aspect correction for basis 1,2",
        "type": float,
        "default": 4.0,  # 2.0 * 2.0
    },
    "aspect 2x2": {
        "description": "Aspect correction for basis 2,2",
        "type": float,
        "default": 1.8,  # 2.0 * 0.9
    },
    "aspect 2x3": {
        "description": "Aspect correction for basis 2,3",
        "type": float,
        "default": 3.0,  # 2.0 * 1.5
    },
    "aspect 2x4": {
        "description": "Aspect correction for basis 2,4",
        "type": float,
        "default": 4.0,  # 2.0 * 2.0
    },
}


def get_default_config() -> Dict[str, Any]:
    """Get default configuration with all keys."""
    return {key: schema["default"] for key, schema in CONFIG_SCHEMA.items()}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from CATPIC_CONFIG environment variable.
    
    Returns:
        Configuration dict merged with defaults
        
    Raises:
        SystemExit: If CATPIC_CONFIG contains invalid JSON
    """
    config = get_default_config()
    
    env_config = os.getenv('CATPIC_CONFIG')
    if not env_config:
        return config
    
    try:
        user_config = json.loads(env_config)
        
        # Validate keys
        for key in user_config:
            if key not in CONFIG_SCHEMA:
                # Suggest similar keys
                suggestions = get_close_matches(key, CONFIG_SCHEMA.keys(), n=3, cutoff=0.6)
                if suggestions:
                    suggestion_text = '\n'.join(f'  "{s}"' for s in suggestions)
                    print(f'Error: Unknown config key "{key}" in CATPIC_CONFIG', file=sys.stderr)
                    print(f'\nDid you mean one of these?\n{suggestion_text}', file=sys.stderr)
                else:
                    print(f'Error: Unknown config key "{key}" in CATPIC_CONFIG', file=sys.stderr)
                print('\nTo fix:', file=sys.stderr)
                print('  1. Check key names: catpic --help config', file=sys.stderr)
                print('  2. Reset to defaults: unset CATPIC_CONFIG', file=sys.stderr)
                print('  3. Re-detect: eval $(catpic --detect)', file=sys.stderr)
                sys.exit(1)
        
        # Merge with defaults (user config takes precedence)
        config.update(user_config)
        
    except json.JSONDecodeError as e:
        print(f'Error: Invalid CATPIC_CONFIG: {e}', file=sys.stderr)
        print('\nTo fix:', file=sys.stderr)
        print('  1. Check syntax: echo "$CATPIC_CONFIG" | jq .', file=sys.stderr)
        print('  2. Reset to defaults: unset CATPIC_CONFIG', file=sys.stderr)
        print('  3. Re-detect: eval $(catpic --detect)', file=sys.stderr)
        sys.exit(1)
    
    return config


def validate_value(key: str, value: Any) -> Any:
    """
    Validate and normalize a config value.
    
    Args:
        key: Configuration key
        value: Value to validate
        
    Returns:
        Normalized value
        
    Raises:
        ValueError: If value is invalid
    """
    if key not in CONFIG_SCHEMA:
        raise ValueError(f'Unknown key "{key}"')
    
    schema = CONFIG_SCHEMA[key]
    
    # Handle null (unset)
    if value is None or value == "" or value == "null":
        return None
    
    # Type conversion
    expected_type = schema["type"]
    try:
        if expected_type == float:
            normalized = float(value)
        elif expected_type == str:
            normalized = str(value).strip()
        else:
            normalized = value
    except (ValueError, TypeError) as e:
        raise ValueError(f'Invalid value for "{key}": {value} ({e})')
    
    # Validate against allowed values
    if "valid" in schema:
        if normalized not in schema["valid"]:
            valid_str = ", ".join(schema["valid"])
            raise ValueError(f'Invalid value for "{key}": {normalized}\nValid values: {valid_str}')
    
    return normalized


def normalize_key(key: str, interactive: bool = True) -> Optional[str]:
    """
    Normalize a key, with optional interactive confirmation.
    
    Args:
        key: User-provided key (may have underscores, hyphens, etc.)
        interactive: If True, prompt for confirmation on fuzzy matches
        
    Returns:
        Canonical key name, or None if rejected/not found
    """
    # Exact match
    if key in CONFIG_SCHEMA:
        return key
    
    # Fuzzy match (convert underscores/hyphens to spaces)
    normalized = key.replace('_', ' ').replace('-', ' ')
    
    if normalized in CONFIG_SCHEMA:
        if interactive:
            # Prompt for confirmation
            response = input(f'Key "{key}" not found. Did you mean "{normalized}"? [y/N]: ')
            if response.lower() == 'y':
                return normalized
            return None
        else:
            # Non-interactive, accept normalization
            return normalized
    
    # No match - suggest similar keys
    suggestions = get_close_matches(key, CONFIG_SCHEMA.keys(), n=3, cutoff=0.6)
    if suggestions:
        suggestion_text = '\n'.join(f'  "{s}"' for s in suggestions)
        print(f'Error: Unknown config key "{key}"', file=sys.stderr)
        print(f'\nDid you mean one of these?\n{suggestion_text}', file=sys.stderr)
    else:
        print(f'Error: Unknown config key "{key}"', file=sys.stderr)
        print('\nValid keys:', file=sys.stderr)
        for k in CONFIG_SCHEMA.keys():
            print(f'  "{k}"', file=sys.stderr)
    
    print('\nSee: catpic --help config', file=sys.stderr)
    return None


def set_config_value(key: str, value: Any, interactive: bool = True) -> Dict[str, Any]:
    """
    Set a configuration value, returning updated full config.
    
    Args:
        key: Configuration key (may need normalization)
        value: Value to set (or None to unset)
        interactive: If True, prompt for confirmation on fuzzy matches
        
    Returns:
        Complete configuration dict with updated value
        
    Raises:
        SystemExit: If key is invalid or value validation fails
    """
    # Normalize key
    canonical_key = normalize_key(key, interactive=interactive)
    if canonical_key is None:
        sys.exit(1)
    
    # Load current config
    config = load_config()
    
    # Validate and set value
    try:
        normalized_value = validate_value(canonical_key, value)
        if normalized_value is None:
            # Unset key
            config.pop(canonical_key, None)
        else:
            config[canonical_key] = normalized_value
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    
    return config


def export_config(config: Dict[str, Any]) -> str:
    """
    Format config as export statement.
    
    Args:
        config: Configuration dict
        
    Returns:
        Shell export command
    """
    # Canonical order: protocol, basis, then aspect_* sorted
    ordered_config = {}
    for key in ["protocol", "basis"]:
        if key in config:
            ordered_config[key] = config[key]
    
    for key in sorted(k for k in config if k.startswith("aspect ")):
        ordered_config[key] = config[key]
    
    json_str = json.dumps(ordered_config, separators=(',', ':'))
    return f"export CATPIC_CONFIG='{json_str}'"


def show_config_help():
    """Print configuration help text."""
    print("Configuration Keys:")
    print()
    
    for key, schema in CONFIG_SCHEMA.items():
        print(f'  "{key}"')
        print(f'    {schema["description"]}')
        
        if "valid" in schema:
            valid_str = ", ".join(schema["valid"])
            print(f'    Valid values: {valid_str}')
        else:
            print(f'    Type: {schema["type"].__name__}')
        
        print(f'    Default: {schema["default"]}')
        print()
    
    print("Examples:")
    print('  catpic --config                    # Show current config')
    print('  catpic --config "protocol" "kitty" # Set protocol')
    print('  catpic --config "aspect 2x4" 1.8   # Set aspect ratio')
    print('  catpic --config "protocol" null    # Unset protocol')
    print()
    print('  eval $(catpic --detect)            # Auto-detect and apply')
    print('  eval $(catpic --config "basis" "2,4")  # Apply change')
