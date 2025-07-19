# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import re
import yaml
from typing import Dict, Any, Optional, List, Tuple

# Field aliases mapping: actual field name -> list of accepted aliases
FIELD_ALIASES = {
    'display_name': ['name', 'displayName', 'display_name', 'customName'],
    'description': ['description', 'desc', 'customDescription'],
}


def _find_actual_field(field_alias: str) -> Optional[str]:
    for actual_field, aliases in FIELD_ALIASES.items():
        if field_alias in aliases:
            return actual_field
    return None


def _get_all_aliases() -> List[str]:
    all_aliases = []
    for aliases in FIELD_ALIASES.values():
        all_aliases.extend(aliases)
    return all_aliases


def _apply_validated_configs(custom_registry: Dict[str, Any], configs: List[Tuple[str, str, str]]) -> None:
    """
    Apply validated configurations to the registry.
    
    :param custom_registry: The registry to modify.
    :param configs: List of tuples (tool_id, field_alias, field_value).
    """
    for tool_id, field_alias, field_value in configs:
        if tool_id not in custom_registry:
            continue
        
        actual_field = _find_actual_field(field_alias)
        if actual_field is None:
            # Log warning for unsupported field
            logging.warning(f"Warning: Unsupported field '{field_alias}' for tool '{tool_id}'.")
            continue
        # Special handling for description length validation
        if actual_field == 'description' and len(field_value) > 1024:
            logging.warning(
                f"Warning: The description for '{field_alias}' exceeds 1024 characters ({len(field_value)}). "
                f"Some LLM models may not support long descriptions."
            )
        custom_registry[tool_id][actual_field] = field_value


def _load_config_from_file(config_from_file: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Load configurations from YAML file data and return as a list of tuples.
    
    :param config_from_file: Configuration data from YAML file.
    :return: List of tuples (tool_id, field_alias, field_value).
    """
    configs = []
    for tool_id, custom_config in config_from_file.items():
        for config_key, config_value in custom_config.items():
            configs.append((tool_id, config_key, config_value))
    return configs


def _load_config_from_cli(cli_tool_overrides: Dict[str, str]) -> List[Tuple[str, str, str]]:
    """
    Load configurations from CLI arguments and return as a list of tuples.
    
    :param cli_tool_overrides: Command line tool overrides.
    :return: List of tuples (tool_id, field_alias, field_value).
    """
    configs = []
    
    # Generate regex pattern dynamically from all available aliases
    all_aliases = _get_all_aliases()
    alias_pattern = '|'.join(re.escape(alias) for alias in all_aliases)
    pattern = rf'tool\.(\w+)\.({alias_pattern})'
    
    for arg, value in cli_tool_overrides.items():
        match = re.match(pattern, arg)
        if match:
            tool_id = match.group(1)
            field_alias = match.group(2)
            configs.append((tool_id, field_alias, value))
    
    return configs


def apply_custom_tool_config(
    tool_registry: Dict[str, Any],
    config_file_path: str,
    cli_tool_overrides: Dict[str, str],
) -> Dict[str, Any]:
    """
    Applies custom configurations to the tool registry from a YAML file and command-line arguments.

    :param tool_registry: The original tool registry.
    :param config_file_path: Path to the YAML configuration file.
    :param cli_tool_overrides: A dictionary of tool overrides from the command line.
    :return: A new tool registry with custom configurations applied.
    """
    custom_registry = copy.deepcopy(tool_registry)
    
    # Load configuration from file
    config_from_file = {}
    if config_file_path:
        try:
            with open(config_file_path, 'r') as f:
                config = yaml.safe_load(f)
                if config and 'tools' in config:
                    config_from_file = config['tools']
        except Exception as e:
            logging.error(f"Error loading tool config file: {e}")

    # Load configurations from both sources
    file_configs = _load_config_from_file(config_from_file)
    cli_configs = _load_config_from_cli(cli_tool_overrides)
    
    # Apply configurations (CLI overrides file configs)
    all_configs = file_configs + cli_configs
    _apply_validated_configs(custom_registry, all_configs)

    return custom_registry
