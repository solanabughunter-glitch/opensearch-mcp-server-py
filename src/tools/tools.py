# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
from .tool_params import (
    GetIndexMappingArgs,
    GetShardsArgs,
    ListIndicesArgs,
    SearchIndexArgs,
    baseToolArgs,
)
from .utils import is_tool_compatible
from opensearch.helper import (
    get_index,
    get_index_mapping,
    get_opensearch_version,
    get_shards,
    list_indices,
    search_index,
)


def check_tool_compatibility(tool_name: str, args: baseToolArgs = None):
    opensearch_version = get_opensearch_version(args)
    if not is_tool_compatible(opensearch_version, TOOL_REGISTRY[tool_name]):
        tool_display_name = TOOL_REGISTRY[tool_name].get('display_name', tool_name)
        min_version = TOOL_REGISTRY[tool_name].get("min_version", "")
        max_version = TOOL_REGISTRY[tool_name].get("max_version", "")

        version_info = (
            f"{min_version} to {max_version}" if min_version and max_version else
            f"{min_version} or later" if min_version else
            f"up to {max_version}" if max_version else
            None
        )

        error_message = f"Tool '{tool_display_name}' is not supported for this OpenSearch version (current version: {opensearch_version})."
        if version_info:
            error_message += f" Supported version: {version_info}."

        raise Exception(error_message)


async def list_indices_tool(args: ListIndicesArgs) -> list[dict]:
    try:
        check_tool_compatibility('ListIndexTool', args)

        # If index is provided, get detailed information for that specific index
        if args.index:
            index_info = get_index(args)
            formatted_info = json.dumps(index_info, indent=2)
            return [
                {'type': 'text', 'text': f'Index information for {args.index}:\n{formatted_info}'}
            ]

        # Otherwise, list all indices with full information
        indices = list_indices(args)
        formatted_indices = json.dumps(indices, indent=2)

        # Return in MCP expected format
        return [{'type': 'text', 'text': f'All indices information:\n{formatted_indices}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error listing indices: {str(e)}'}]


async def get_index_mapping_tool(args: GetIndexMappingArgs) -> list[dict]:
    try:
        check_tool_compatibility('IndexMappingTool', args)
        mapping = get_index_mapping(args)
        formatted_mapping = json.dumps(mapping, indent=2)

        return [{'type': 'text', 'text': f'Mapping for {args.index}:\n{formatted_mapping}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting mapping: {str(e)}'}]


async def search_index_tool(args: SearchIndexArgs) -> list[dict]:
    try:
        check_tool_compatibility('SearchIndexTool', args)
        result = search_index(args)
        formatted_result = json.dumps(result, indent=2)

        return [
            {
                'type': 'text',
                'text': f'Search results from {args.index}:\n{formatted_result}',
            }
        ]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error searching index: {str(e)}'}]


async def get_shards_tool(args: GetShardsArgs) -> list[dict]:
    try:
        check_tool_compatibility('GetShardsTool', args)
        result = get_shards(args)

        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting shards: {result["error"]}'}]
        formatted_text = 'index | shard | prirep | state | docs | store | ip | node\n'

        # Format each shard row
        for shard in result:
            formatted_text += f'{shard["index"]} | '
            formatted_text += f'{shard["shard"]} | '
            formatted_text += f'{shard["prirep"]} | '
            formatted_text += f'{shard["state"]} | '
            formatted_text += f'{shard["docs"]} | '
            formatted_text += f'{shard["store"]} | '
            formatted_text += f'{shard["ip"]} | '
            formatted_text += f'{shard["node"]}\n'

        return [{'type': 'text', 'text': formatted_text}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting shards information: {str(e)}'}]


# Registry of available OpenSearch tools with their metadata
TOOL_REGISTRY = {
    'ListIndexTool': {
        'display_name': 'ListIndexTool',
        'description': 'Lists all indices in the OpenSearch cluster with full information including docs.count, docs.deleted, store.size, etc. If an index parameter is provided, returns detailed information about that specific index.',
        'input_schema': ListIndicesArgs.model_json_schema(),
        'function': list_indices_tool,
        'args_model': ListIndicesArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'IndexMappingTool': {
        'display_name': 'IndexMappingTool',
        'description': 'Retrieves index mapping and setting information for an index in OpenSearch',
        'input_schema': GetIndexMappingArgs.model_json_schema(),
        'function': get_index_mapping_tool,
        'args_model': GetIndexMappingArgs,
        'http_methods': 'GET',
    },
    'SearchIndexTool': {
        'display_name': 'SearchIndexTool',
        'description': 'Searches an index using a query written in query domain-specific language (DSL) in OpenSearch',
        'input_schema': SearchIndexArgs.model_json_schema(),
        'function': search_index_tool,
        'args_model': SearchIndexArgs,
        'http_methods': 'GET, POST',
    },
    'GetShardsTool': {
        'display_name': 'GetShardsTool',
        'description': 'Gets information about shards in OpenSearch',
        'input_schema': GetShardsArgs.model_json_schema(),
        'function': get_shards_tool,
        'args_model': GetShardsArgs,
        'http_methods': 'GET',
    },
}
