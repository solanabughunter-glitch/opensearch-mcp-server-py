import pytest
from semver import Version
from tools.common import is_tool_compatible


class TestIsToolCompatible:
    def test_version_within_range(self):
        tool_info = {"min_version": "1.0.0", "max_version": "3.0.0"}
        assert is_tool_compatible(Version.parse("2.0.0"), tool_info) is True

    def test_version_below_min(self):
        tool_info = {"min_version": "2.0.0", "max_version": "3.0.0"}
        assert is_tool_compatible(Version.parse("1.5.0"), tool_info) is False

    def test_version_above_max(self):
        tool_info = {"min_version": "1.0.0", "max_version": "2.0.0"}
        assert is_tool_compatible(Version.parse("2.1.0"), tool_info) is False

    def test_version_equal_to_min(self):
        tool_info = {"min_version": "1.0.0", "max_version": "3.0.0"}
        assert is_tool_compatible(Version.parse("1.0.0"), tool_info) is True

    def test_version_equal_to_max(self):
        tool_info = {"min_version": "1.0.0", "max_version": "3.0.0"}
        assert is_tool_compatible(Version.parse("3.0.0"), tool_info) is True

    def test_version_only_patch_not_provided(self):
        tool_info = {"min_version": "2.5", "max_version": "3"}
        assert is_tool_compatible(Version.parse("2.5.1"), tool_info) is True
        assert is_tool_compatible(Version.parse("2.15.0"), tool_info) is True
        assert is_tool_compatible(Version.parse("3.0.0"), tool_info) is True

    def test_default_tool_info(self):
        # Should be True for almost any reasonable version
        assert is_tool_compatible(Version.parse("1.2.3")) is True
        assert is_tool_compatible(Version.parse("99.0.0")) is True
        assert is_tool_compatible(Version.parse("0.0.1")) is True

    def test_invalid_version_strings(self):
        # If min_version or max_version is not a valid semver, should raise ValueError
        with pytest.raises(ValueError):
            is_tool_compatible(Version.parse("1.0.0"), {"min_version": "not_a_version"})
        with pytest.raises(ValueError):
            is_tool_compatible(Version.parse("1.0.0"), {"max_version": "not_a_version"})
