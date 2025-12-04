# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Configuration validation module for OpenSearch MCP Server.

Provides schema validation and enhanced error handling for YAML configuration files.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, ValidationError
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)


class ClusterConfig(BaseModel):
    """Validation model for individual cluster configuration."""
    
    opensearch_url: str = Field(..., description="OpenSearch cluster URL")
    iam_arn: Optional[str] = Field(None, description="AWS IAM role ARN for authentication")
    aws_region: Optional[str] = Field(None, description="AWS region for the cluster")
    opensearch_username: Optional[str] = Field(None, description="Username for basic authentication")
    opensearch_password: Optional[str] = Field(None, description="Password for basic authentication")
    profile: Optional[str] = Field(None, description="AWS profile name")
    is_serverless: Optional[bool] = Field(None, description="Whether this is an OpenSearch Serverless cluster")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Connection timeout in seconds (1-300)")
    opensearch_no_auth: Optional[bool] = Field(None, description="Disable authentication for this cluster")
    ssl_verify: Optional[bool] = Field(None, description="Verify SSL certificates")
    opensearch_header_auth: Optional[bool] = Field(None, description="Enable header-based authentication")

    @validator('opensearch_url')
    def validate_url(cls, v):
        """Validate OpenSearch URL format."""
        if not v or not v.strip():
            raise ValueError('OpenSearch URL cannot be empty')
        
        try:
            parsed = urlparse(v.strip())
            if not parsed.scheme or not parsed.netloc:
                raise ValueError('Invalid URL format')
            if parsed.scheme not in ['http', 'https']:
                raise ValueError('URL must use http or https scheme')
        except Exception as e:
            raise ValueError(f'Invalid OpenSearch URL: {e}')
        
        return v.strip()

    @validator('iam_arn')
    def validate_iam_arn(cls, v):
        """Validate AWS IAM ARN format."""
        if v is None:
            return v
        
        arn_pattern = r'^arn:aws:iam::\d{12}:role/[a-zA-Z0-9+=,.@_-]+$'
        if not re.match(arn_pattern, v):
            raise ValueError('Invalid IAM ARN format. Expected: arn:aws:iam::123456789012:role/RoleName')
        
        return v

    @validator('aws_region')
    def validate_aws_region(cls, v):
        """Validate AWS region format."""
        if v is None:
            return v
        
        # Pattern supports standard regions (us-east-1), GovCloud (us-gov-west-1), and China (cn-north-1)
        region_pattern = r'^[a-z]{2}(-gov)?-[a-z]+-\d+$'
        if not re.match(region_pattern, v):
            raise ValueError('Invalid AWS region format. Expected: us-east-1, us-gov-west-1, eu-west-2, etc.')
        
        return v

    @validator('opensearch_username')
    def validate_username(cls, v):
        """Validate username format."""
        if v is not None and (not v.strip() or len(v.strip()) < 1):
            raise ValueError('Username cannot be empty if provided')
        return v.strip() if v else v

    @validator('opensearch_password')
    def validate_password(cls, v):
        """Validate password format."""
        # Note: Passwords are not stripped to preserve intentional whitespace
        if v is not None and len(v) < 1:
            raise ValueError('Password cannot be empty if provided')
        return v

    @validator('profile')
    def validate_profile(cls, v):
        """Validate AWS profile name."""
        if v is not None and (not v.strip() or len(v.strip()) < 1):
            raise ValueError('Profile name cannot be empty if provided')
        
        # AWS profile names should be alphanumeric with hyphens and underscores
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValueError('Profile name contains invalid characters')
        
        return v.strip() if v else v

    def validate_authentication_consistency(self) -> List[str]:
        """Validate authentication method consistency."""
        warnings = []
        
        # Check for conflicting authentication methods
        auth_methods = [
            self.opensearch_username and self.opensearch_password,
            self.iam_arn,
            self.profile,
            self.opensearch_no_auth,
            self.opensearch_header_auth
        ]
        
        active_methods = [i for i, method in enumerate(auth_methods) if method]
        
        if len(active_methods) > 1:
            method_names = ['basic_auth', 'iam_role', 'aws_profile', 'no_auth', 'header_auth']
            conflicting = [method_names[i] for i in active_methods]
            warnings.append(f"Multiple authentication methods configured: {', '.join(conflicting)}")
        
        # Check for missing required fields
        if self.opensearch_username and not self.opensearch_password:
            warnings.append("Username provided but password is missing")
        
        if self.opensearch_password and not self.opensearch_username:
            warnings.append("Password provided but username is missing")
        
        if self.iam_arn and not self.aws_region:
            warnings.append("IAM role ARN provided but AWS region is missing")
        
        # Serverless-specific checks
        if self.is_serverless and self.opensearch_url and not self.opensearch_url.endswith('.aoss.amazonaws.com'):
            warnings.append("Serverless mode enabled but URL doesn't appear to be an OpenSearch Serverless endpoint")
        
        return warnings


class ToolCustomization(BaseModel):
    """Validation model for tool customization."""
    
    display_name: Optional[str] = Field(None, description="Custom display name for the tool")
    description: Optional[str] = Field(None, description="Custom description for the tool")
    args: Optional[Dict[str, str]] = Field(None, description="Custom argument descriptions")

    @validator('display_name')
    def validate_display_name(cls, v):
        """Validate tool display name."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError('Display name cannot be empty')
        
        # Must match pattern: alphanumeric, hyphens, underscores only
        pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(pattern, v.strip()):
            raise ValueError('Display name can only contain letters, numbers, hyphens, and underscores')
        
        if len(v.strip()) > 50:
            raise ValueError('Display name cannot exceed 50 characters')
        
        return v.strip()

    @validator('args')
    def validate_args(cls, v):
        """Validate argument descriptions."""
        if v is None:
            return v
        
        if not isinstance(v, dict):
            raise ValueError('Args must be a dictionary')
        
        for arg_name, description in v.items():
            if not isinstance(arg_name, str) or not arg_name.strip():
                raise ValueError('Argument names must be non-empty strings')
            
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f'Argument description for "{arg_name}" must be a non-empty string')
            
            if len(description) > 200:
                raise ValueError(f'Argument description for "{arg_name}" cannot exceed 200 characters')
        
        return v


class ToolCategory(BaseModel):
    """Validation model for tool categories."""
    
    category_name: str = Field(..., description="Name of the tool category")
    tools: List[str] = Field(..., description="List of tool names in this category")

    @validator('category_name')
    def validate_category_name(cls, v):
        """Validate category name."""
        if not v.strip():
            raise ValueError('Category name cannot be empty')
        
        pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(pattern, v.strip()):
            raise ValueError('Category name can only contain letters, numbers, hyphens, and underscores')
        
        return v.strip()

    @validator('tools')
    def validate_tools(cls, v):
        """Validate tool list."""
        if not v:
            raise ValueError('Tool category must contain at least one tool')
        
        for tool in v:
            if not isinstance(tool, str) or not tool.strip():
                raise ValueError('Tool names must be non-empty strings')
        
        return [tool.strip() for tool in v]


class ToolFilter(BaseModel):
    """Validation model for tool filtering configuration."""
    
    enabled_tools: Optional[List[str]] = Field(None, description="List of enabled tools")
    disabled_tools: Optional[List[str]] = Field(None, description="List of disabled tools")
    enabled_categories: Optional[List[str]] = Field(None, description="List of enabled categories")
    disabled_categories: Optional[List[str]] = Field(None, description="List of disabled categories")
    enabled_tools_regex: Optional[List[str]] = Field(None, description="List of enabled tool regex patterns")
    disabled_tools_regex: Optional[List[str]] = Field(None, description="List of disabled tool regex patterns")
    settings: Optional[Dict[str, Any]] = Field(None, description="Tool filter settings")

    @validator('settings')
    def validate_settings(cls, v):
        """Validate tool filter settings."""
        if v is None:
            return v
        
        if not isinstance(v, dict):
            raise ValueError('Settings must be a dictionary')
        
        # Validate allow_write setting
        if 'allow_write' in v and not isinstance(v['allow_write'], bool):
            raise ValueError('allow_write setting must be a boolean')
        
        return v

    def validate_filter_consistency(self) -> List[str]:
        """Validate filter configuration consistency."""
        warnings = []
        
        # Check for conflicting enable/disable
        if self.enabled_tools and self.disabled_tools:
            common_tools = set(self.enabled_tools) & set(self.disabled_tools)
            if common_tools:
                warnings.append(f"Tools both enabled and disabled: {', '.join(common_tools)}")
        
        if self.enabled_categories and self.disabled_categories:
            common_categories = set(self.enabled_categories) & set(self.disabled_categories)
            if common_categories:
                warnings.append(f"Categories both enabled and disabled: {', '.join(common_categories)}")
        
        return warnings


class ServerConfig(BaseModel):
    """Main configuration validation model."""
    
    version: str = Field(..., description="Configuration version")
    description: Optional[str] = Field(None, description="Configuration description")
    clusters: Optional[Dict[str, ClusterConfig]] = Field(None, description="Cluster configurations")
    tools: Optional[Dict[str, ToolCustomization]] = Field(None, description="Tool customizations")
    tool_category: Optional[Dict[str, List[str]]] = Field(None, description="Tool categories")
    tool_filters: Optional[ToolFilter] = Field(None, description="Tool filtering configuration")

    @validator('version')
    def validate_version(cls, v):
        """Validate configuration version."""
        if not v.strip():
            raise ValueError('Version cannot be empty')
        
        # Simple semantic version validation
        version_pattern = r'^\d+\.\d+(\.\d+)?$'
        if not re.match(version_pattern, v.strip()):
            raise ValueError('Version must be in semantic version format (e.g., "1.0", "1.2.3")')
        
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        """Validate configuration description."""
        if v is None:
            return v
        
        if len(v.strip()) > 500:
            raise ValueError('Description cannot exceed 500 characters')
        
        return v.strip()

    def validate_configuration(self) -> Dict[str, List[str]]:
        """Perform comprehensive configuration validation."""
        validation_result = {
            'errors': [],
            'warnings': []
        }
        
        # Validate cluster configurations
        if self.clusters is not None:
            if len(self.clusters) == 0:
                validation_result['warnings'].append("Clusters section is empty - no clusters configured")
            else:
                for cluster_name, cluster_config in self.clusters.items():
                    # Validate cluster name
                    if not cluster_name.strip():
                        validation_result['errors'].append("Cluster name cannot be empty")
                    elif not re.match(r'^[a-zA-Z0-9_-]+$', cluster_name):
                        validation_result['errors'].append(f"Invalid cluster name '{cluster_name}': only letters, numbers, hyphens, and underscores allowed")
                    
                    # Validate cluster configuration
                    cluster_warnings = cluster_config.validate_authentication_consistency()
                    for warning in cluster_warnings:
                        validation_result['warnings'].append(f"Cluster '{cluster_name}': {warning}")
        
        # Validate tool customizations
        if self.tools:
            # Check for duplicate display names
            display_names = []
            for tool_name, tool_config in self.tools.items():
                if tool_config.display_name:
                    if tool_config.display_name in display_names:
                        validation_result['errors'].append(f"Duplicate display name '{tool_config.display_name}' found")
                    else:
                        display_names.append(tool_config.display_name)
        
        # Validate tool categories
        if self.tool_category:
            for category_name, tools in self.tool_category.items():
                if not tools:
                    validation_result['errors'].append(f"Tool category '{category_name}' cannot be empty")
        
        # Validate tool filters
        if self.tool_filters:
            filter_warnings = self.tool_filters.validate_filter_consistency()
            validation_result['warnings'].extend(filter_warnings)
        
        return validation_result


class ConfigurationValidator:
    """Main configuration validator class."""
    
    @staticmethod
    def validate_config_file(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a complete configuration file.
        
        Args:
            config_data: Raw configuration dictionary from YAML
            
        Returns:
            Dictionary with validation results including errors, warnings, and normalized config
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'normalized_config': None
        }
        
        try:
            # Parse and validate the configuration
            config = ServerConfig(**config_data)
            
            # Perform comprehensive validation
            validation_result = config.validate_configuration()
            
            # Collect all errors and warnings
            result['errors'].extend(validation_result['errors'])
            result['warnings'].extend(validation_result['warnings'])
            
            # If no errors, mark as valid and return normalized config
            if not result['errors']:
                result['valid'] = True
                result['normalized_config'] = config.dict() if hasattr(config, 'dict') else config.model_dump()
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                message = error['msg']
                result['errors'].append(f"Field '{field_path}': {message}")
        
        except Exception as e:
            result['errors'].append(f"Unexpected validation error: {str(e)}")
        
        return result
    
    @staticmethod
    def validate_cluster_only(cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate only cluster configuration (for partial validation).
        
        Args:
            cluster_data: Raw cluster configuration dictionary
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'normalized_config': None
        }
        
        try:
            cluster = ClusterConfig(**cluster_data)
            warnings = cluster.validate_authentication_consistency()
            
            result['warnings'].extend(warnings)
            
            if not result['errors']:
                result['valid'] = True
                result['normalized_config'] = cluster.dict() if hasattr(cluster, 'dict') else cluster.model_dump()
                
        except ValidationError as e:
            for error in e.errors():
                field_path = '.'.join(str(x) for x in error['loc'])
                message = error['msg']
                result['errors'].append(f"Field '{field_path}': {message}")
        
        except Exception as e:
            result['errors'].append(f"Unexpected validation error: {str(e)}")
        
        return result
