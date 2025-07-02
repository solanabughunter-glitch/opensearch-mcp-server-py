![OpenSearch logo](https://github.com/opensearch-project/opensearch-py/raw/main/OpenSearch.svg)

# OpenSearch MCP Server с поддержкой Dashboards API

> **Форк от:** [opensearch-project/opensearch-mcp-server-py](https://github.com/opensearch-project/opensearch-mcp-server-py)
> 
> **Основные улучшения:**
> - ✅ Поддержка OpenSearch Dashboards API
> - ✅ Подключение когда прямой API недоступен  
> - ✅ Полная совместимость с оригинальным MCP сервером
> 
> 📖 **[Подробнее о изменениях в форке](FORK_CHANGES.md)**

- [OpenSearch MCP Server](#opensearch-mcp-server)
- [Установка](#installing-opensearch-mcp-server-py)
- [Доступные инструменты](#available-tools)
- [Быстрый старт](#user-guide)

## OpenSearch MCP Server
**opensearch-mcp-server-py** is a Model Context Protocol (MCP) server for OpenSearch that enables AI assistants to interact with OpenSearch clusters. It provides a standardized interface for AI models to perform operations like searching indices, retrieving mappings, and managing shards through both stdio and streaming (SSE/Streamable HTTP) protocols.

**Key features:**
- Seamless integration with AI assistants and LLMs through the MCP protocol
- Support for both stdio and streaming server transports (SSE and Streamable HTTP)
- Built-in tools for common OpenSearch operations
- Easy integration with Claude Desktop and LangChain
- Secure authentication using basic auth or IAM roles
- **NEW**: OpenSearch Dashboards API support - connect when direct OpenSearch API is not available

## Installing opensearch-mcp-server-py

### Using uv (recommended)
```bash
# Clone the forked repository with Dashboards API support
git clone https://github.com/VladMain/opensearch-mcp-server-py.git
cd opensearch-mcp-server-py

# Install with uv
uv sync

# Run the server
uv run mcp-server-opensearch --config your_config.yml
```

### Using pip
Opensearch-mcp-server-py can be installed from [PyPI](https://pypi.org/project/opensearch-mcp-server-py/) via pip:
```bash
pip install opensearch-mcp-server-py
```

### OpenSearch Dashboards Support
This fork includes support for connecting through OpenSearch Dashboards API when direct OpenSearch access is not available. See `FORT_OPENSEARCH_SETUP.md` for detailed setup instructions.

## Available Tools
- [ListIndexTool](https://docs.opensearch.org/docs/latest/api-reference/cat/cat-indices/): Lists all indices in OpenSearch.
- [IndexMappingTool](https://docs.opensearch.org/docs/latest/ml-commons-plugin/agents-tools/tools/index-mapping-tool/): Retrieves index mapping and setting information for an index in OpenSearch.
- [SearchIndexTool](https://docs.opensearch.org/docs/latest/ml-commons-plugin/agents-tools/tools/search-index-tool/): Searches an index using a query written in query domain-specific language (DSL) in OpenSearch.
- [GetShardsTool](https://docs.opensearch.org/docs/latest/api-reference/cat/cat-shards/): Gets information about shards in OpenSearch.
- [ClusterHealthTool](https://docs.opensearch.org/docs/latest/api-reference/cluster-api/cluster-health/): Returns basic information about the health of the cluster.
- [CountTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/count/): Returns number of documents matching a query.
- [ExplainTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/explain/): Returns information about why a specific document matches (or doesn't match) a query.
- [MsearchTool](https://docs.opensearch.org/docs/latest/api-reference/search-apis/multi-search/): Allows to execute several search operations in one request.

### Tool Parameters
- **ListIndexTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to

- **IndexMappingTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (required): The name of the index to retrieve mappings for

- **SearchIndexTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (required): The name of the index to search in
    - `query` (required): The search query in OpenSearch Query DSL format

- **GetShardsTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (required): The name of the index to get shard information for
    
- **ClusterHealthTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (optional): Limit health reporting to a specific index

- **CountTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (optional): The name of the index to count documents in
    - `body` (optional): Query in JSON format to filter documents

- **ExplainTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (required): The name of the index to retrieve the document from
    - `id` (required): The document ID to explain
    - `body` (required): Query in JSON format to explain against the document

- **MsearchTool**
    - `opensearch_url` (optional): The OpenSearch cluster URL to connect to
    - `index` (optional): Default index to search in
    - `body` (required): Multi-search request body in NDJSON format

> More tools coming soon. [Click here](DEVELOPER_GUIDE.md#contributing)

## User Guide
For detailed usage instructions, configuration options, and examples, please see the [User Guide](USER_GUIDE.md).

## Contributing
Interested in contributing? Check out our:
- [Development Guide](DEVELOPER_GUIDE.md#opensearch-mcp-server-py-developer-guide) - Setup your development environment
- [Contributing Guidelines](DEVELOPER_GUIDE.md#contributing) - Learn how to contribute

## Code of Conduct
This project has adopted the [Amazon Open Source Code of Conduct](CODE_OF_CONDUCT.md). For more information see the [Code of Conduct FAQ](https://aws.github.io/code-of-conduct-faq), or contact [opensource-codeofconduct@amazon.com](mailto:opensource-codeofconduct@amazon.com) with any additional questions or comments.

## License
This project is licensed under the [Apache v2.0 License](LICENSE.txt).

## Copyright
Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.