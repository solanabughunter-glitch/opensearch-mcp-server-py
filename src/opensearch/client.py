# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

from opensearchpy import OpenSearch, RequestsHttpConnection
from urllib.parse import urlparse
from requests_aws4auth import AWS4Auth
import os
import boto3
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
OPENSEARCH_SERVICE = "es"

# This file should expose the OpenSearch py client
def initialize_client() -> OpenSearch:
    """
    Initialize and return an OpenSearch client with appropriate authentication.
    
    The function attempts to authenticate in the following order:
    1. Basic authentication using OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD
    2. AWS IAM authentication using boto3 credentials
    
    Returns:
        OpenSearch: Configured OpenSearch client
        
    Raises:
        ValueError: If OPENSEARCH_URL is not set
        RuntimeError: If no valid authentication method is available
    """
    opensearch_url = os.getenv("OPENSEARCH_URL", "")
    opensearch_username = os.getenv("OPENSEARCH_USERNAME", "")
    opensearch_password = os.getenv("OPENSEARCH_PASSWORD", "")
    aws_region = os.getenv("AWS_REGION", "")

    if not opensearch_url:
        raise ValueError("OPENSEARCH_URL environment variable is not set")

    # Parse the OpenSearch domain URL
    parsed_url = urlparse(opensearch_url)

    # Common client configuration
    client_kwargs: Dict[str, Any] = {
        'hosts': [opensearch_url],
        'use_ssl': (parsed_url.scheme == "https"),
        'verify_certs': True,
        'connection_class': RequestsHttpConnection,
    }

    # 1. Try basic auth
    if opensearch_username and opensearch_password:
        client_kwargs['http_auth'] = (opensearch_username, opensearch_password)
        return OpenSearch(**client_kwargs)

    # 2. Try to get credentials (boto3 session)
    try:
        credentials = boto3.Session().get_credentials()
        if credentials:
            aws_auth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                aws_region,
                OPENSEARCH_SERVICE,
                session_token=credentials.token
            )
            client_kwargs['http_auth'] = aws_auth
            return OpenSearch(**client_kwargs)
    except (boto3.exceptions.Boto3Error, Exception) as e:
        logger.error(f"Failed to get AWS credentials: {str(e)}")

    raise RuntimeError("No valid AWS or basic authentication provided for OpenSearch")


client = initialize_client()