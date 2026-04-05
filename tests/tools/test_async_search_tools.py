# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestAsyncSearchTools:
    def setup_method(self):
        """Setup that runs before each test method."""
        self.mock_client = Mock()
        self.mock_client.transport.perform_request = AsyncMock(return_value={})
        self.mock_client.info = AsyncMock(return_value={'version': {'number': '2.19.0'}})

        self.init_client_patcher = patch(
            'opensearch.client.initialize_client', return_value=self.mock_client
        )
        self.init_client_patcher.start()

        import sys
        modules_to_clear = ['tools.tools']
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        from tools.tools import (
            submit_async_search_tool,
            get_async_search_tool,
            delete_async_search_tool,
        )
        from tools.tool_params import (
            SubmitAsyncSearchArgs,
            GetAsyncSearchArgs,
            DeleteAsyncSearchArgs,
        )

        self._submit_async_search_tool = submit_async_search_tool
        self._get_async_search_tool = get_async_search_tool
        self._delete_async_search_tool = delete_async_search_tool
        self.SubmitAsyncSearchArgs = SubmitAsyncSearchArgs
        self.GetAsyncSearchArgs = GetAsyncSearchArgs
        self.DeleteAsyncSearchArgs = DeleteAsyncSearchArgs

    def teardown_method(self):
        self.init_client_patcher.stop()

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_success(self):
        """Test submitting an async search returns search ID and state."""
        mock_response = {
            'id': 'FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            'state': 'RUNNING',
            'start_time_in_millis': 1234567890000,
        }
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.SubmitAsyncSearchArgs(
            index='my-index',
            query_dsl={'query': {'match_all': {}}},
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert len(result) == 1
        assert result[0]['type'] == 'text'
        assert 'Async search submitted' in result[0]['text']
        assert 'FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc' in result[0]['text']
        assert 'RUNNING' in result[0]['text']
        self.mock_client.transport.perform_request.assert_called_once()
        call_args = self.mock_client.transport.perform_request.call_args
        assert call_args.kwargs['method'] == 'POST'
        assert '/my-index/_plugins/_asynchronous_search' in call_args.kwargs['url']

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_with_custom_params(self):
        """Test that async search query parameters are passed correctly."""
        mock_response = {'id': 'test-id', 'state': 'RUNNING'}
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.SubmitAsyncSearchArgs(
            index='logs-*',
            query_dsl={'query': {'range': {'timestamp': {'gte': 'now-1h'}}}},
            wait_for_completion_timeout='10s',
            keep_on_completion=True,
            keep_alive='1h',
            size=50,
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert 'Async search submitted' in result[0]['text']
        call_args = self.mock_client.transport.perform_request.call_args
        params = call_args.kwargs['params']
        assert params['wait_for_completion_timeout'] == '10s'
        assert params['keep_on_completion'] == 'true'
        assert params['keep_alive'] == '1h'

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_can_disable_keep_on_completion(self):
        """Test that keep_on_completion can be explicitly disabled."""
        mock_response = {'id': 'test-id', 'state': 'RUNNING'}
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.SubmitAsyncSearchArgs(
            index='logs-*',
            query_dsl={'query': {'match_all': {}}},
            keep_on_completion=False,
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert 'Async search submitted' in result[0]['text']
        call_args = self.mock_client.transport.perform_request.call_args
        params = call_args.kwargs['params']
        assert params['keep_on_completion'] == 'false'

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_size_capped(self):
        """Test that size is capped at max_size_limit (100)."""
        mock_response = {'id': 'test-id', 'state': 'RUNNING'}
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.SubmitAsyncSearchArgs(
            index='my-index',
            query_dsl={'query': {'match_all': {}}},
            size=500,
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert 'Async search submitted' in result[0]['text']
        call_args = self.mock_client.transport.perform_request.call_args
        body = json.loads(call_args.kwargs['body'])
        assert body['size'] == 100

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_error(self):
        """Test error handling when async search submission fails."""
        self.mock_client.transport.perform_request = AsyncMock(
            side_effect=Exception('Connection refused')
        )

        args = self.SubmitAsyncSearchArgs(
            index='my-index',
            query_dsl={'query': {'match_all': {}}},
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert len(result) == 1
        assert result[0].get('is_error') or 'error' in result[0]['text'].lower()

    @pytest.mark.asyncio
    async def test_submit_async_search_tool_string_query_dsl(self):
        """Test that string query_dsl is accepted and parsed."""
        mock_response = {'id': 'test-id', 'state': 'RUNNING'}
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.SubmitAsyncSearchArgs(
            index='my-index',
            query_dsl='{"query": {"match_all": {}}}',
            opensearch_cluster_name='',
        )
        result = await self._submit_async_search_tool(args)

        assert 'Async search submitted' in result[0]['text']

    @pytest.mark.asyncio
    async def test_get_async_search_tool_running(self):
        """Test getting status of a running async search."""
        mock_response = {
            'id': 'FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            'state': 'RUNNING',
            'start_time_in_millis': 1234567890000,
        }
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.GetAsyncSearchArgs(
            search_id='FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            opensearch_cluster_name='',
        )
        result = await self._get_async_search_tool(args)

        assert len(result) == 1
        assert 'Async search results' in result[0]['text']
        assert 'RUNNING' in result[0]['text']
        self.mock_client.transport.perform_request.assert_called_once_with(
            method='GET',
            url='/_plugins/_asynchronous_search/FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
        )

    @pytest.mark.asyncio
    async def test_get_async_search_tool_succeeded(self):
        """Test getting results of a completed async search."""
        mock_response = {
            'id': 'FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            'state': 'SUCCEEDED',
            'response': {
                'hits': {
                    'total': {'value': 42, 'relation': 'eq'},
                    'hits': [{'_index': 'my-index', '_id': '1', '_source': {'title': 'test'}}],
                }
            },
        }
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.GetAsyncSearchArgs(
            search_id='FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            opensearch_cluster_name='',
        )
        result = await self._get_async_search_tool(args)

        assert 'SUCCEEDED' in result[0]['text']
        assert '"total":{"value":42' in result[0]['text']

    @pytest.mark.asyncio
    async def test_get_async_search_tool_error(self):
        """Test error handling when getting async search fails."""
        self.mock_client.transport.perform_request = AsyncMock(
            side_effect=Exception('Search ID not found')
        )

        args = self.GetAsyncSearchArgs(
            search_id='nonexistent-id',
            opensearch_cluster_name='',
        )
        result = await self._get_async_search_tool(args)

        assert result[0].get('is_error') or 'error' in result[0]['text'].lower()

    @pytest.mark.asyncio
    async def test_delete_async_search_tool_success(self):
        """Test deleting an async search successfully."""
        mock_response = {'acknowledged': True}
        self.mock_client.transport.perform_request = AsyncMock(return_value=mock_response)

        args = self.DeleteAsyncSearchArgs(
            search_id='FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
            opensearch_cluster_name='',
        )
        result = await self._delete_async_search_tool(args)

        assert len(result) == 1
        assert 'deleted' in result[0]['text'].lower()
        assert 'FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc' in result[0]['text']
        self.mock_client.transport.perform_request.assert_called_once_with(
            method='DELETE',
            url='/_plugins/_asynchronous_search/FklfVGlYbkpRVl9FbVlVcDJfRTBhQXc',
        )

    @pytest.mark.asyncio
    async def test_delete_async_search_tool_error(self):
        """Test error handling when deleting async search fails."""
        self.mock_client.transport.perform_request = AsyncMock(
            side_effect=Exception('Search ID not found')
        )

        args = self.DeleteAsyncSearchArgs(
            search_id='nonexistent-id',
            opensearch_cluster_name='',
        )
        result = await self._delete_async_search_tool(args)

        assert result[0].get('is_error') or 'error' in result[0]['text'].lower()
