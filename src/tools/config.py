# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
import re
import yaml
from typing import Dict, Any


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
    config_from_file = {}
    if config_file_path:
        try:
            with open(config_file_path, 'r') as f:
                config = yaml.safe_load(f)
                if config and 'tools' in config:
                    config_from_file = config['tools']
        except Exception as e:
            logging.error(f"Error loading tool config file: {e}")

    # Apply config from file
    for tool_id, custom_config in config_from_file.items():
        if tool_id in custom_registry:
            if 'display_name' in custom_config:
                custom_registry[tool_id]['display_name'] = custom_config['display_name']
            if 'description' in custom_config:
                description = custom_config['description']
                if len(description) > 1024:
                    logging.warning(
                        f"Warning: The description for tool '{tool_id}' exceeds 1024 characters ({len(description)}). "
                        f"Some LLM models may not support long descriptions."
                    )
                custom_registry[tool_id]['description'] = description

    # Apply config from command line arguments (overrides file config)
    for arg, value in cli_tool_overrides.items():
        match = re.match(r'tool\.(\w+)\.(name|displayName|description)', arg)
        if match:
            tool_id = match.group(1)
            prop_alias = match.group(2)
            prop_key = (
                'display_name'
                if prop_alias.lower() in ['name', 'displayname']
                else 'description'
            )

            if tool_id in custom_registry:
                if prop_key == 'description':
                    if len(value) > 1024:
                        logging.warning(
                            f"Warning: The description for tool '{tool_id}' from CLI override exceeds 1024 characters ({len(value)}). "
                            f"Some LLM models may not support descriptions this long."
                        )
                custom_registry[tool_id][prop_key] = value

    return custom_registry
