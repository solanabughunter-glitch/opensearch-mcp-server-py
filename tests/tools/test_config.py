# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import copy
import os
import yaml
from tools.config import apply_custom_tool_config

MOCK_TOOL_REGISTRY = {
    'ListIndexTool': {
        'display_name': 'ListIndexTool',
        'description': 'Original description for ListIndexTool',
        'other_field': 'some_value',
    },
    'SearchIndexTool': {
        'display_name': 'SearchIndexTool',
        'description': 'Original description for SearchIndexTool',
    },
}

def test_apply_config_from_yaml_file():
    """Test that tool names and descriptions are updated from a YAML file."""
    config_content = {
        'tools': {
            'ListIndexTool': {
                'display_name': 'YAML Custom Name',
                'description': 'YAML custom description.',
            },
            'SearchIndexTool': {'display_name': 'YAML Searcher'},
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, config_path, {})

    assert custom_registry['ListIndexTool']['display_name'] == 'YAML Custom Name'
    assert custom_registry['ListIndexTool']['description'] == 'YAML custom description.'
    assert custom_registry['SearchIndexTool']['display_name'] == 'YAML Searcher'
    # Ensure other fields are untouched
    assert custom_registry['ListIndexTool']['other_field'] == 'some_value'
    # Ensure original is untouched
    assert registry['ListIndexTool']['display_name'] == 'ListIndexTool'

    os.remove(config_path)


def test_apply_config_from_cli_args():
    """Test that tool names and descriptions are updated from CLI arguments."""
    cli_overrides = {
        'tool.ListIndexTool.displayName': 'CLI Custom Name',
        'tool.SearchIndexTool.description': 'CLI custom description.',
    }
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, '', cli_overrides)

    assert custom_registry['ListIndexTool']['display_name'] == 'CLI Custom Name'
    assert custom_registry['SearchIndexTool']['description'] == 'CLI custom description.'


def test_cli_overrides_yaml():
    """Test that CLI arguments override YAML file configurations."""
    config_content = {
        'tools': {
            'ListIndexTool': {
                'display_name': 'YAML Custom Name',
                'description': 'YAML description.',
            }
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    cli_overrides = {
        'tool.ListIndexTool.name': 'CLI Final Name',
    }

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, config_path, cli_overrides)

    assert custom_registry['ListIndexTool']['display_name'] == 'CLI Final Name'
    assert custom_registry['ListIndexTool']['description'] == 'YAML description.'

    os.remove(config_path)


def test_cli_name_alias():
    """Test that 'name' alias works for 'display_name' in CLI arguments."""
    cli_overrides = {'tool.ListIndexTool.name': 'CLI Name Alias'}
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, '', cli_overrides)

    assert custom_registry['ListIndexTool']['display_name'] == 'CLI Name Alias'


def test_long_description_warning_from_yaml(caplog):
    """Test that a warning is logged for long descriptions from a YAML file."""
    long_description = 'a' * 1025
    config_content = {
        'tools': {
            'ListIndexTool': {'description': long_description},
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    apply_custom_tool_config(registry, config_path, {})

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert "exceeds 1024 characters" in caplog.text
    assert "ListIndexTool" in caplog.text

    os.remove(config_path)


def test_long_description_warning_from_cli(caplog):
    """Test that a warning is logged for long descriptions from CLI arguments."""
    long_description = 'b' * 1025
    cli_overrides = {'tool.SearchIndexTool.description': long_description}

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    apply_custom_tool_config(registry, '', cli_overrides)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert "exceeds 1024 characters" in caplog.text
    assert "SearchIndexTool" in caplog.text 