# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field
from typing import Any


class baseToolArgs(BaseModel):
    """Base class for all tool arguments that contains common OpenSearch connection parameters."""

    opensearch_cluster_name: str = Field(
        default='', description='The name of the OpenSearch cluster'
    )


class ListIndicesArgs(baseToolArgs):
    index: str = Field(
        default='',
        description='The name of the index to get detailed information for. If provided, returns detailed information about this specific index instead of listing all indices.',
    )
    include_detail: bool = Field(
        default=True,
        description='Whether to include detailed information. When listing indices (no index specified), if False, returns only a pure list of index names. If True, returns full metadata. When a specific index is provided, detailed information (including mappings) will be returned.',
    )


class GetIndexMappingArgs(baseToolArgs):
    index: str = Field(description='The name of the index to get mapping information for')


class SearchIndexArgs(baseToolArgs):
    index: str = Field(description='The name of the index to search in')
    query: Any = Field(description='The search query in OpenSearch query DSL format')


class GetShardsArgs(baseToolArgs):
    index: str = Field(description='The name of the index to get shard information for')


class AggregationsArgs(baseToolArgs):
    """Arguments for AggregationsTool (aggs-only search)."""

    index: str | None = Field(
        default=None,
        description="Index or pattern (optional, e.g. 'logs-*').",
    )
    aggs: Any = Field(
        ...,
        description='Aggregations JSON object (buckets/metrics/pipelines).',
    )
    query: Any | None = Field(
        default=None,
        description='Optional filter query (OpenSearch Query DSL).',
    )
    timeout: str = Field(
        default='5s',
        description="Shard-level timeout (e.g., '5s', '500ms').",
    )
    track_total_hits: bool = Field(
        default=False,
        description='Accurate hit count; unused by aggs but accepted for parity.',
    )
    raw: bool = Field(
        default=False,
        description='If true, return full raw OpenSearch response instead of trimmed output.',
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {
                    'index': 'logs-*',
                    'query': {'range': {'@timestamp': {'gte': 'now-7d'}}},
                    'aggs': {'by_status': {'terms': {'field': 'status.keyword', 'size': 5}}},
                    'timeout': '5s',
                    'track_total_hits': False,
                    'raw': False,
                }
            ]
        }
