from .tools import TOOL_REGISTRY
from semver import Version


def is_tool_compatible(current_version: Version, tool_info: dict = {}):
    # use opensearch_url if provided, otherwise use the environment variable
    min_tool_version = Version.parse(
        tool_info.get("min_version", "0.0.0"), optional_minor_and_patch=True
    )
    max_tool_version = Version.parse(
        tool_info.get("max_version", "99.99.99"), optional_minor_and_patch=True
    )
    return min_tool_version <= current_version <= max_tool_version


def get_enabled_tools(version: str) -> dict:
    enabled = {}
    for name, info in TOOL_REGISTRY.items():
        if is_tool_compatible(version, info):
            enabled[name] = info
    return enabled
