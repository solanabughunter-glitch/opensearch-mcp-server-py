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


def test_yaml_field_aliases():
    """Test that various field aliases work correctly in YAML configuration."""
    config_content = {
        'tools': {
            'ListIndexTool': {
                'name': 'YAML Name Alias',  # Should map to display_name
                'desc': 'YAML Desc Alias',  # Should map to description
            },
            'SearchIndexTool': {
                'displayName': 'YAML DisplayName Alias',  # Should map to display_name
                'description': 'Regular Description',      # Direct mapping
            },
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, config_path, {})

    assert custom_registry['ListIndexTool']['display_name'] == 'YAML Name Alias'
    assert custom_registry['ListIndexTool']['description'] == 'YAML Desc Alias'
    assert custom_registry['SearchIndexTool']['display_name'] == 'YAML DisplayName Alias'
    assert custom_registry['SearchIndexTool']['description'] == 'Regular Description'

    os.remove(config_path)


def test_cli_field_aliases():
    """Test that various field aliases work correctly in CLI arguments."""
    cli_overrides = {
        'tool.ListIndexTool.name': 'CLI Name Alias',
        'tool.ListIndexTool.desc': 'CLI Desc Alias',
        'tool.SearchIndexTool.displayName': 'CLI DisplayName Alias',
        'tool.SearchIndexTool.description': 'CLI Regular Description',
    }
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, '', cli_overrides)

    assert custom_registry['ListIndexTool']['display_name'] == 'CLI Name Alias'
    assert custom_registry['ListIndexTool']['description'] == 'CLI Desc Alias'
    assert custom_registry['SearchIndexTool']['display_name'] == 'CLI DisplayName Alias'
    assert custom_registry['SearchIndexTool']['description'] == 'CLI Regular Description'


def test_unsupported_fields_ignored():
    """Test that unsupported field names are ignored in both YAML and CLI."""
    config_content = {
        'tools': {
            'ListIndexTool': {
                'name': 'Valid Name',
                'unsupported_field': 'Should be ignored',
                'another_invalid': 'Also ignored',
            },
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    cli_overrides = {
        'tool.ListIndexTool.description': 'Valid Description',
        'tool.ListIndexTool.invalid_field': 'Should be ignored',
        'tool.InvalidTool.name': 'Non-existent tool, should be ignored',
    }

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, config_path, cli_overrides)

    # Valid changes should be applied
    assert custom_registry['ListIndexTool']['display_name'] == 'Valid Name'
    assert custom_registry['ListIndexTool']['description'] == 'Valid Description'
    
    # Invalid fields should not be added to the registry
    assert 'unsupported_field' not in custom_registry['ListIndexTool']
    assert 'another_invalid' not in custom_registry['ListIndexTool']
    assert 'invalid_field' not in custom_registry['ListIndexTool']
    
    # Non-existent tools should not be added
    assert 'InvalidTool' not in custom_registry
    
    # Other fields should remain unchanged
    assert custom_registry['ListIndexTool']['other_field'] == 'some_value'

    os.remove(config_path)


def test_yaml_unsupported_field_warning(caplog):
    """Test that warnings are logged for unsupported fields in YAML configuration."""
    config_content = {
        'tools': {
            'ListIndexTool': {
                'name': 'Valid Name',
                'invalid_field': 'Should trigger warning',
                'another_bad_field': 'Also triggers warning',
            },
        }
    }
    config_path = 'test_temp_config.yml'
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)

    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, config_path, {})

    # Valid field should be applied
    assert custom_registry['ListIndexTool']['display_name'] == 'Valid Name'
    
    # Check that warnings were logged
    assert len(caplog.records) == 2
    warning_messages = [record.message for record in caplog.records]
    
    assert any("Unsupported field 'invalid_field'" in msg for msg in warning_messages)
    assert any("Unsupported field 'another_bad_field'" in msg for msg in warning_messages)

    os.remove(config_path)


def test_cli_unsupported_field_ignored():
    """Test that CLI arguments with unsupported fields are ignored by regex pattern."""
    cli_overrides = {
        'tool.ListIndexTool.name': 'Valid Name',
        'tool.ListIndexTool.invalid_field': 'Should be ignored by regex',
        'tool.SearchIndexTool.bad_field': 'Also ignored by regex',
        'invalid.format': 'Wrong format entirely',
    }
    
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    custom_registry = apply_custom_tool_config(registry, '', cli_overrides)

    # Only valid field should be applied
    assert custom_registry['ListIndexTool']['display_name'] == 'Valid Name'
    
    # Invalid fields should not be added
    assert 'invalid_field' not in custom_registry['ListIndexTool']
    assert 'bad_field' not in custom_registry['SearchIndexTool']


def test_field_aliases_structure():
    """Test that the FIELD_ALIASES structure and utility functions work correctly."""
    from tools.config import FIELD_ALIASES, _find_actual_field, _get_all_aliases
    
    # Test the structure
    assert 'display_name' in FIELD_ALIASES
    assert 'description' in FIELD_ALIASES
    assert isinstance(FIELD_ALIASES['display_name'], list)
    assert isinstance(FIELD_ALIASES['description'], list)
    
    # Test _find_actual_field function
    assert _find_actual_field('name') == 'display_name'
    assert _find_actual_field('displayName') == 'display_name'
    assert _find_actual_field('display_name') == 'display_name'
    assert _find_actual_field('customName') == 'display_name'
    assert _find_actual_field('description') == 'description'
    assert _find_actual_field('desc') == 'description'
    assert _find_actual_field('customDescription') == 'description'
    assert _find_actual_field('invalid_field') is None
    
    # Test _get_all_aliases function
    all_aliases = _get_all_aliases()
    expected_aliases = ['name', 'displayName', 'display_name', 'customName', 'description', 'desc', 'customDescription']
    for alias in expected_aliases:
        assert alias in all_aliases


def test_load_config_from_file():
    """Test the _load_config_from_file function directly."""
    from tools.config import _load_config_from_file
    
    config_data = {
        'tool1': {
            'name': 'Tool One',
            'description': 'First tool',
        },
        'tool2': {
            'displayName': 'Tool Two',
        }
    }
    
    configs = _load_config_from_file(config_data)
    
    # Should return list of tuples
    assert len(configs) == 3
    assert ('tool1', 'name', 'Tool One') in configs
    assert ('tool1', 'description', 'First tool') in configs
    assert ('tool2', 'displayName', 'Tool Two') in configs


def test_load_config_from_cli():
    """Test the _load_config_from_cli function directly."""
    from tools.config import _load_config_from_cli
    
    cli_overrides = {
        'tool.tool1.name': 'CLI Tool One',
        'tool.tool2.description': 'CLI Tool Two Description',
        'invalid.format': 'Should be ignored',
        'tool.tool3.invalid_field': 'Should be ignored by regex',
    }
    
    configs = _load_config_from_cli(cli_overrides)
    
    # Should return list of tuples, ignoring invalid formats
    assert len(configs) == 2
    assert ('tool1', 'name', 'CLI Tool One') in configs
    assert ('tool2', 'description', 'CLI Tool Two Description') in configs


def test_apply_validated_configs():
    """Test the _apply_validated_configs function directly."""
    from tools.config import _apply_validated_configs
    
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    
    configs = [
        ('ListIndexTool', 'name', 'New Name'),
        ('ListIndexTool', 'description', 'New Description'),
        ('NonExistentTool', 'name', 'Should be ignored'),
    ]
    
    _apply_validated_configs(registry, configs)
    
    # Valid changes should be applied
    assert registry['ListIndexTool']['display_name'] == 'New Name'
    assert registry['ListIndexTool']['description'] == 'New Description'
    
    # Non-existent tool should not be added
    assert 'NonExistentTool' not in registry


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


def test_long_description_warning_with_aliases(caplog):
    """Test that warnings are logged for long descriptions using aliases."""
    long_description = 'c' * 1025
    
    # Test YAML with desc alias
    config_content = {
        'tools': {
            'ListIndexTool': {'desc': long_description},
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

    os.remove(config_path)
    caplog.clear()

    # Test CLI with desc alias
    cli_overrides = {'tool.SearchIndexTool.desc': long_description}
    registry = copy.deepcopy(MOCK_TOOL_REGISTRY)
    apply_custom_tool_config(registry, '', cli_overrides)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'WARNING'
    assert "exceeds 1024 characters" in caplog.text 