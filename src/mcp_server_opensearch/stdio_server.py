# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from mcp_server_opensearch.clusters_information import load_clusters_from_yaml
from tools.tool_filter import get_tools
from tools.tool_generator import generate_tools_from_openapi
from tools.tools import TOOL_REGISTRY
from tools.config import apply_custom_tool_config


# --- Server setup ---
async def serve(
    mode: str = 'single',
    profile: str = '',
    config_file_path: str = '',
    cli_tool_overrides: dict = None,
) -> None:
    # Set the global profile if provided
    if profile:
        from opensearch.client import set_profile

        set_profile(profile)

    server = Server('opensearch-mcp-server')
    # Load clusters from YAML file
    if mode == 'multi':
        load_clusters_from_yaml(config_file_path)

    # Call tool generator and tool filter
    await generate_tools_from_openapi()
    customized_registry = apply_custom_tool_config(
        TOOL_REGISTRY, config_file_path, cli_tool_overrides or {}
    )
    enabled_tools = get_tools(
        tool_registry=customized_registry, mode=mode, config_file_path=config_file_path
    )
    logging.info(f'Enabled tools: {list(enabled_tools.keys())}')

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for tool_name, tool_info in enabled_tools.items():
            tools.append(
                Tool(
                    name=tool_info.get('display_name', tool_name),
                    description=tool_info['description'],
                    inputSchema=tool_info['input_schema'],
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        # Find the tool by its display name, which is what the client sees
        found_tool_key = None
        for key, tool_info in enabled_tools.items():
            if tool_info.get('display_name', key) == name:
                found_tool_key = key
                break

        if not found_tool_key:
            raise ValueError(f'Unknown or disabled tool: {name}')

        tool = enabled_tools.get(found_tool_key)
        parsed = tool['args_model'](**arguments)
        return await tool['function'](parsed)

    # Start stdio-based MCP server
    options = server.create_initialization_options()
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, options, raise_exceptions=True)
