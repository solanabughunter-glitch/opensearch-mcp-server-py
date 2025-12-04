#!/usr/bin/env python3
# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Configuration validation utility for OpenSearch MCP Server.

This script can be used to validate YAML configuration files before deploying
the MCP server. It provides detailed error messages and warnings.
"""

import argparse
import json
import logging
import sys
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tools.config_validator import ConfigurationValidator


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_config_file(file_path: str, verbose: bool = False) -> bool:
    """
    Validate a configuration file and print results.
    
    Args:
        file_path: Path to the YAML configuration file
        verbose: Enable verbose logging
        
    Returns:
        True if validation passed, False otherwise
    """
    try:
        # Read the configuration file
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if not config_data:
            print(f"ERROR: Configuration file '{file_path}' is empty or invalid")
            return False
        
        # Validate the configuration
        print(f"Validating configuration file: {file_path}")
        print("=" * 60)
        
        validation_result = ConfigurationValidator.validate_config_file(config_data)
        
        # Print results
        if validation_result['valid']:
            print("SUCCESS: Configuration is VALID")
            
            # Print summary
            normalized_config = validation_result['normalized_config']
            clusters = normalized_config.get('clusters', {}) or {}
            tools = normalized_config.get('tools', {}) or {}
            categories = normalized_config.get('tool_category', {}) or {}
            filters = normalized_config.get('tool_filters')
            
            print(f"\nConfiguration Summary:")
            print(f"   • Version: {normalized_config.get('version', 'N/A')}")
            print(f"   • Clusters: {len(clusters)}")
            print(f"   • Tool customizations: {len(tools)}")
            print(f"   • Tool categories: {len(categories) if categories else 0}")
            print(f"   • Tool filters: {'Configured' if filters else 'None'}")
            
            if clusters:
                print(f"\nClusters:")
                for name, cluster in clusters.items():
                    auth_methods = []
                    if cluster.get('opensearch_username'):
                        auth_methods.append('basic_auth')
                    if cluster.get('iam_arn'):
                        auth_methods.append('iam_role')
                    if cluster.get('profile'):
                        auth_methods.append('aws_profile')
                    if cluster.get('opensearch_no_auth'):
                        auth_methods.append('no_auth')
                    if cluster.get('opensearch_header_auth'):
                        auth_methods.append('header_auth')
                    
                    serverless = " (Serverless)" if cluster.get('is_serverless') else ""
                    print(f"   • {name}{serverless} - Auth: {', '.join(auth_methods) or 'None'}")
        
        else:
            print("ERROR: Configuration is INVALID")
        
        # Print errors
        if validation_result['errors']:
            print(f"\nErrors ({len(validation_result['errors'])}):")
            for i, error in enumerate(validation_result['errors'], 1):
                print(f"   {i}. {error}")
        
        # Print warnings
        if validation_result['warnings']:
            print(f"\nWarnings ({len(validation_result['warnings'])}):")
            for i, warning in enumerate(validation_result['warnings'], 1):
                print(f"   {i}. {warning}")
        
        print("=" * 60)
        
        return validation_result['valid']
        
    except FileNotFoundError:
        print(f"ERROR: File '{file_path}' not found")
        return False
    except yaml.YAMLError as e:
        print(f"YAML ERROR: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False


def create_sample_config():
    """Create a sample configuration file with validation examples."""
    sample_config = {
        "version": "1.0",
        "description": "Sample OpenSearch MCP Server Configuration",
        "clusters": {
            "valid-cluster": {
                "opensearch_url": "https://localhost:9200",
                "opensearch_username": "admin",
                "opensearch_password": "password",
                "ssl_verify": False,
                "timeout": 30
            },
            "invalid-cluster": {
                "opensearch_url": "invalid-url",  # This will cause validation error
                "iam_arn": "invalid-arn",  # This will cause validation error
                "aws_region": "invalid-region"  # This will cause validation error
            }
        },
        "tools": {
            "ListIndexTool": {
                "display_name": "CustomIndexLister",
                "description": "Custom description for listing indices"
            }
        },
        "tool_category": {
            "search_tools": ["SearchIndexTool", "MsearchTool"],
            "management_tools": ["ListIndexTool"]
        },
        "tool_filters": {
            "enabled_tools": ["ListIndexTool", "SearchIndexTool"],
            "disabled_tools": ["GetClusterStateTool"],
            "settings": {
                "allow_write": True
            }
        }
    }
    
    sample_file = Path("sample_config_with_validation.yml")
    with open(sample_file, 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f, default_flow_style=False, indent=2)
    
    print(f"Created sample configuration file: {sample_file}")
    print("   This file contains both valid and invalid configurations for testing.")
    return str(sample_file)


def main():
    """Main entry point for the validation utility."""
    parser = argparse.ArgumentParser(
        description="Validate OpenSearch MCP Server configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a configuration file
  python validate_config.py config.yml
  
  # Validate with verbose output
  python validate_config.py config.yml --verbose
  
  # Create a sample configuration file
  python validate_config.py --create-sample
  
  # Validate and output JSON results
  python validate_config.py config.yml --json
        """
    )
    
    parser.add_argument(
        'config_file',
        nargs='?',
        help='Path to the YAML configuration file to validate'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output validation results in JSON format'
    )
    
    parser.add_argument(
        '--create-sample',
        action='store_true',
        help='Create a sample configuration file with validation examples'
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Handle create sample flag
    if args.create_sample:
        sample_file = create_sample_config()
        if args.config_file:
            # Also validate the provided file
            is_valid = validate_config_file(args.config_file, args.verbose)
            if args.json:
                # Output JSON results would require modifying validate_config_file
                pass
            sys.exit(0 if is_valid else 1)
        sys.exit(0)
    
    # Require config file unless creating sample
    if not args.config_file:
        parser.print_help()
        print("\nERROR: Configuration file is required")
        sys.exit(1)
    
    # Validate the configuration
    is_valid = validate_config_file(args.config_file, args.verbose)
    
    if args.json:
        # For JSON output, we'd need to modify the validation function
        # to return structured data instead of printing
        print("JSON output not yet implemented")
        sys.exit(1)
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
