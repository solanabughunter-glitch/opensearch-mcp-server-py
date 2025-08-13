# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from semver import Version
from tools.tool_params import *

# Configure logging
logger = logging.getLogger(__name__)

from .client import get_client

from typing import Any, Optional, Dict
from opensearchpy import OpenSearch
# List all the helper functions, these functions perform a single rest call to opensearch
# these functions will be used in tools folder to eventually write more complex tools
def list_indices(args: ListIndicesArgs) -> json:
    from .client import initialize_client

    client = initialize_client(args)
    response = client.cat.indices(format='json')
    return response


def get_index(args: ListIndicesArgs) -> json:
    """Get detailed information about a specific index.

    Args:
        args: ListIndicesArgs containing the index name

    Returns:
        json: Detailed index information including settings and mappings
    """
    from .client import initialize_client

    client = initialize_client(args)
    response = client.indices.get(index=args.index)
    return response


def get_index_mapping(args: GetIndexMappingArgs) -> json:
    from .client import initialize_client

    client = initialize_client(args)
    response = client.indices.get_mapping(index=args.index)
    return response


def search_index(args: SearchIndexArgs) -> json:
    from .client import initialize_client

    client = initialize_client(args)
    response = client.search(index=args.index, body=args.query)
    return response


def get_shards(args: GetShardsArgs) -> json:
    from .client import initialize_client

    client = initialize_client(args)
    response = client.cat.shards(index=args.index, format='json')
    return response


def get_opensearch_version(args: baseToolArgs) -> Version:
    """Get the version of OpenSearch cluster.

    Returns:
        Version: The version of OpenSearch cluster (SemVer style)
    """
    from .client import initialize_client

    try:
        client = initialize_client(args)
        response = client.info()
        return Version.parse(response['version']['number'])
    except Exception as e:
        logger.error(f'Error getting OpenSearch version: {e}')
        return None
def _to_seconds(val: Optional[str | float | int]) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().lower()
    try:
        if s.endswith("ms"):
            return max(0.001, float(s[:-2]) / 1000.0)
        if s.endswith("s"):
            return max(0.001, float(s[:-1]))
        if s.endswith("m"):
            return max(0.001, float(s[:-1]) * 60.0)
        if s.endswith("h"):
            return max(0.001, float(s[:-1]) * 3600.0)
        return max(0.001, float(s))
    except Exception:
        return None

def run_aggregations(args: AggregationsArgs) -> Dict[str, Any]:
    """Single REST call to OpenSearch with size:0 + aggregations."""
    if not isinstance(args.aggs, dict):
        raise ValueError("aggs must be a JSON object (dict)")
    client: OpenSearch = get_client()

    body: Dict[str, Any] = {
        "size": 0,
        "aggs": args.aggs,
        "track_total_hits": bool(args.track_total_hits),
    }
    if args.query:
        body["query"] = args.query
    if args.timeout:
        body["timeout"] = args.timeout  # shard-level timeout (e.g., "5s")

    # HTTP client timeout in seconds
    req_timeout = _to_seconds(args.timeout)

    resp = client.search(
        index=args.index or "*",
        body=body,
        request_timeout=req_timeout,
        # Optional: filter_path to shrink payload if you don't need hits/_shards
        # filter_path="took,timed_out,aggregations.*"  # uncomment if desired
    )
    return resp