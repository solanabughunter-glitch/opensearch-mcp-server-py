# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import yaml
from pydantic import BaseModel
from typing import Dict, Optional
from tools.config_validator import ConfigurationValidator, ClusterConfig


class ClusterInfo(BaseModel):
    """Model representing OpenSearch cluster configuration."""

    opensearch_url: str
    iam_arn: Optional[str] = None
    aws_region: Optional[str] = None
    opensearch_username: Optional[str] = None
    opensearch_password: Optional[str] = None
    profile: Optional[str] = None
    is_serverless: Optional[bool] = None
    timeout: Optional[int] = None
    opensearch_no_auth: Optional[bool] = None
    ssl_verify: Optional[bool] = None
    opensearch_header_auth: Optional[bool] = None


# Global dictionary to store cluster information
# Key: string name (cluster identifier)
# Value: ClusterInfo object containing cluster configuration
cluster_registry: Dict[str, ClusterInfo] = {}


def add_cluster(name: str, cluster_info: ClusterInfo) -> None:
    """Add a cluster configuration to the global registry.

    Args:
        name: String identifier for the cluster
        cluster_info: ClusterInfo object containing cluster configuration
    """
    cluster_registry[name] = cluster_info


def get_cluster(name: str) -> Optional[ClusterInfo]:
    """Retrieve cluster configuration by name.

    Args:
        name: String identifier for the cluster

    Returns:
        ClusterInfo: Cluster configuration or None if not found
    """
    return cluster_registry.get(name)


async def load_clusters_from_yaml(file_path: str) -> None:
    """Load cluster configurations from a YAML file and populate the global registry.

    Args:
        file_path: Path to the YAML configuration file

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        PermissionError: If the file cannot be read due to permissions
        yaml.YAMLError: If the YAML file is malformed
        UnicodeDecodeError: If the file has encoding issues
        OSError: For other file system related errors
        ValueError: If the configuration validation fails
    """
    if not file_path:
        return

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'YAML file not found: {file_path}')

    result = {'loaded_clusters': [], 'errors': [], 'warnings': [], 'validation_errors': []}

    try:
        # Try to open and read the file with proper error handling
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
        except PermissionError as e:
            raise PermissionError(f'Permission denied reading YAML file {file_path}: {str(e)}')
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(
                e.encoding,
                e.object,
                e.start,
                e.end,
                f'Encoding error reading YAML file {file_path}: {str(e)}',
            )
        except OSError as e:
            raise OSError(f'OS error reading YAML file {file_path}: {str(e)}')

        # Validate the entire configuration first
        validation_result = ConfigurationValidator.validate_config_file(config or {})
        
        # Log validation warnings
        for warning in validation_result.get('warnings', []):
            logging.warning(f'Configuration warning: {warning}')
            result['warnings'].append(warning)
        
        # Check for validation errors
        if validation_result.get('errors'):
            error_msg = 'Configuration validation failed:'
            for error in validation_result['errors']:
                error_msg += f'\n  - {error}'
                result['validation_errors'].append(error)
            logging.error(error_msg)
            raise ValueError(error_msg)

        # Get normalized configuration
        normalized_config = validation_result.get('normalized_config', {})
        clusters = normalized_config.get('clusters', {})
        result['total_clusters'] = len(clusters)
        logging.info(f'Total clusters found in config file: {result["total_clusters"]}')

        # Process each validated cluster
        for cluster_name, cluster_config in clusters.items():
            try:
                # Create ClusterInfo from validated configuration
                cluster_info = ClusterInfo(
                    opensearch_url=cluster_config['opensearch_url'],
                    iam_arn=cluster_config.get('iam_arn'),
                    aws_region=cluster_config.get('aws_region'),
                    opensearch_username=cluster_config.get('opensearch_username'),
                    opensearch_password=cluster_config.get('opensearch_password'),
                    profile=cluster_config.get('profile'),
                    is_serverless=cluster_config.get('is_serverless'),
                    timeout=cluster_config.get('timeout'),
                    opensearch_no_auth=cluster_config.get('opensearch_no_auth'),
                    ssl_verify=cluster_config.get('ssl_verify'),
                    opensearch_header_auth=cluster_config.get('opensearch_header_auth'),
                )

                # Add cluster to registry
                add_cluster(name=cluster_name, cluster_info=cluster_info)
                result['loaded_clusters'].append(cluster_name)
                logging.info(f'Successfully loaded cluster: {cluster_name}')

            except Exception as e:
                error_msg = f"Error processing cluster '{cluster_name}': {str(e)}"
                result['errors'].append(error_msg)
                logging.error(error_msg)

        # Final summary
        if result['loaded_clusters']:
            logging.info(f'Successfully loaded {len(result["loaded_clusters"])} clusters: {result["loaded_clusters"]}')
        else:
            logging.warning('No clusters were successfully loaded')
        
        if result['errors']:
            logging.error(f'Loading errors: {result["errors"]}')
        
        # Return summary for potential monitoring/telemetry
        return result

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f'Invalid YAML format in {file_path}: {str(e)}')
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logging.error(f'Unexpected error loading clusters from {file_path}: {e}')
        raise
