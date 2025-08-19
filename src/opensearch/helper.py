# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import logging
from semver import Version
from tools.tool_params import *

# Configure logging
logger = logging.getLogger(__name__)

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


# ---------------------------- NEW: Aggregations helper ----------------------------

def _maybe_dump(model_or_dict):
    """Return a plain dict if a pydantic model is passed, otherwise the value itself."""
    return model_or_dict.model_dump() if hasattr(model_or_dict, "model_dump") else model_or_dict


def run_aggregations(args: AggregationsArgs) -> dict:
    """
    Executes an aggregations-only search.

    Behavior:
      - requires args.index and args.aggs
      - sets size=0 (no hits) to keep this tool focused on aggregations
      - includes args.query if provided
      - forwards track_total_hits (bool) and body-level timeout if present

    Returns the full OpenSearch response (so the tool can either return raw or trim it).
    """
    from .client import initialize_client

    if not getattr(args, "index", None):
        raise ValueError("AggregationsTool requires 'index'.")
    aggs = getattr(args, "aggs", None) or getattr(args, "aggregations", None)
    if aggs is None:
        raise ValueError("AggregationsTool requires 'aggs'.")

    client = initialize_client(args)

    body = {"size": 0, "aggs": _maybe_dump(aggs)}

    q = getattr(args, "query", None)
    if q is not None:
        body["query"] = _maybe_dump(q)

    if getattr(args, "track_total_hits", None) is not None:
        body["track_total_hits"] = bool(args.track_total_hits)

    # Body-level shard timeout like "5s" (kept optional)
    if getattr(args, "timeout", None):
        body["timeout"] = args.timeout

    # Keep the call minimal (no extra kwargs) to match existing helper style
    return client.search(index=args.index, body=body)
