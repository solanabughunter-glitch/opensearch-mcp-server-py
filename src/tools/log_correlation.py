# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import logging
import re
from .tool_logging import log_tool_error
from .tool_params import LogCorrelationArgs
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)

LOG_LEVELS = {
    10: 'TRACE',
    20: 'DEBUG',
    30: 'INFO',
    40: 'WARN',
    50: 'ERROR',
    60: 'FATAL',
}

LEVEL_NAME_TO_INT = {
    'trace': 10,
    'debug': 20,
    'info': 30,
    'warn': 40,
    'error': 50,
    'fatal': 60,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts/lists."""
    current = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current if current is not None else default


def _tenant_to_index_slug(tenant_name: str) -> str:
    """Convert 'mccoy/aiccdev' → 'mccoy-aiccdev'."""
    return tenant_name.replace('/', '-')


def _parse_time_range(time_range: str) -> Tuple[str, str]:
    """Convert a human-readable time range to OpenSearch gte/lte values."""
    tr = time_range.lower().strip()
    match = re.match(
        r'last\s+(\d+)\s+(hours?|minutes?|days?|h|m|d)',
        tr,
    )
    if match:
        amount = int(match.group(1))
        unit = match.group(2)[0]  # h, m, or d
        return f'now-{amount}{unit}', 'now'
    return time_range, 'now'


# ---------------------------------------------------------------------------
# Query builders
# ---------------------------------------------------------------------------


def _time_range_clause(gte: str, lte: str) -> dict:
    return {
        'range': {
            '@timestamp': {
                'gte': gte,
                'lte': lte,
                'format': 'strict_date_optional_time||epoch_millis',
            }
        }
    }


def _tenant_query(
    tenant_name: str,
    gte: str,
    lte: str,
    level_filter: Optional[int] = None,
    keyword: Optional[str] = None,
) -> dict:
    """Query for indices that store tenantName at the top level."""
    must = [
        {'term': {'tenantName.keyword': tenant_name}},
        _time_range_clause(gte, lte),
    ]
    if level_filter is not None:
        must.append({'range': {'level': {'gte': level_filter}}})
    if keyword:
        must.append({'multi_match': {'query': keyword, 'fields': ['msg', 'rawLog.moduleName']}})
    return {'query': {'bool': {'must': must}}, 'sort': [{'@timestamp': {'order': 'desc'}}]}


def _per_tenant_query(
    gte: str,
    lte: str,
    level_filter: Optional[int] = None,
    keyword: Optional[str] = None,
) -> dict:
    """Query for per-tenant indices where the index name already filters the tenant."""
    must: List[dict] = [_time_range_clause(gte, lte)]
    if level_filter is not None:
        must.append({'range': {'level': {'gte': level_filter}}})
    if keyword:
        must.append({'query_string': {'query': f'*{keyword}*'}})
    return {'query': {'bool': {'must': must}}, 'sort': [{'@timestamp': {'order': 'desc'}}]}


def _connection_id_query(connection_id: str) -> dict:
    return {
        'query': {
            'bool': {
                'should': [
                    {'term': {'connection.id.keyword': connection_id}},
                    {'match': {'rawLog.data.event.connection.id': connection_id}},
                ],
                'minimum_should_match': 1,
            }
        },
        'sort': [{'@timestamp': {'order': 'desc'}}],
    }


def _session_id_query(session_id: str) -> dict:
    return {
        'query': {
            'bool': {
                'should': [
                    {'match': {'event.original.data.event.session.id': session_id}},
                    {'match': {'rawLog.data.event.session.id': session_id}},
                ],
                'minimum_should_match': 1,
            }
        },
        'sort': [{'@timestamp': {'order': 'desc'}}],
    }


# ---------------------------------------------------------------------------
# Correlation ID collection for second-pass queries
# ---------------------------------------------------------------------------


def _collect_correlation_ids(logs: List[dict]) -> Dict[str, set]:
    """Extract unique correlation IDs from normalized logs for cross-service matching."""
    ids: Dict[str, set] = {
        'connectionIds': set(),
        'sessionIds': set(),
        'requestIds': set(),
        'clientIds': set(),
        'contextIds': set(),
    }
    for log in logs:
        for field, key in [
            ('connectionId', 'connectionIds'),
            ('connectionToken', 'connectionIds'),
            ('sessionId', 'sessionIds'),
            ('sessionToken', 'sessionIds'),
            ('requestId', 'requestIds'),
            ('clientId', 'clientIds'),
            ('contextId', 'contextIds'),
        ]:
            val = log.get(field, '')
            if val:
                ids[key].add(val)
    return ids


# ---------------------------------------------------------------------------
# Fetcher — parallel queries against OpenSearch
# ---------------------------------------------------------------------------


async def _query_index(args: LogCorrelationArgs, index: str, body: dict, size: int) -> dict:
    """Run a single search query, returning an empty-style result on failure."""
    from opensearch.client import get_opensearch_client

    try:
        async with get_opensearch_client(args) as client:
            query = dict(body)
            query['size'] = min(size, 100)
            return await client.search(index=index, body=query)
    except Exception as exc:
        logger.warning('Error querying %s: %s', index, exc)
        return {'hits': {'total': {'value': 0}, 'hits': []}, '_error': str(exc)}


_CORR_FIELD_MAP = {
    'stream-server': {
        'connectionId': ['rawLog.data.call.data.connectionId'],
        'sessionId': ['rawLog.data.call.data.sessionId'],
        'requestId': ['rawLog.data.requestId'],
        'contextId': ['rawLog.data.contextId'],
    },
    'nlp-server': {
        'connectionId': ['metadata.connection_id'],
        'sessionId': ['metadata.session_id'],
        'requestId': ['metadata.request_id', 'request_id'],
        'clientId': ['metadata.client_id'],
    },
}


async def _query_by_correlation_ids(
    args: LogCorrelationArgs,
    index: str,
    time_clause: dict,
    corr_ids: Dict[str, set],
    source_tag: str,
    size: int,
) -> dict:
    """Query an index by matching known correlation IDs (second pass)."""
    field_map = _CORR_FIELD_MAP.get(source_tag, {})
    should_clauses: List[dict] = []

    id_to_key = [
        ('connectionIds', 'connectionId'),
        ('sessionIds', 'sessionId'),
        ('requestIds', 'requestId'),
        ('clientIds', 'clientId'),
        ('contextIds', 'contextId'),
    ]
    for id_set_key, field_key in id_to_key:
        vals = list(corr_ids.get(id_set_key, set()))
        if not vals:
            continue
        fields = field_map.get(field_key, [])
        for field in fields:
            if len(vals) == 1:
                should_clauses.append({'match': {field: vals[0]}})
            else:
                should_clauses.append({'terms': {f'{field}.keyword': vals[:50]}})

    if not should_clauses:
        return {'hits': {'total': {'value': 0}, 'hits': []}}

    body = {
        'query': {
            'bool': {
                'must': [time_clause],
                'should': should_clauses,
                'minimum_should_match': 1,
            }
        },
        'sort': [{'@timestamp': {'order': 'desc'}}],
    }
    return await _query_index(args, index, body, size)


# ---------------------------------------------------------------------------
# Normalizers — one per index type
# ---------------------------------------------------------------------------


def _norm_bot_engine_default(hit: dict) -> dict:
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    metadata = data.get('metadata', {})
    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'bot-engine.default',
        'tenantName': s.get('tenantName', ''),
        'agentName': s.get('agentName', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': s.get('msg', ''),
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'podName': _safe_get(s, 'kubernetes', 'pod_name', default=''),
        'namespace': _safe_get(s, 'kubernetes', 'namespace_name', default=''),
        'connectionId': metadata.get('connectionId', '') or _safe_get(data, 'event', 'connection', 'id', default=''),
        'sessionId': metadata.get('sessionId', '') or _safe_get(data, 'event', 'session', 'id', default=''),
        'channelCode': metadata.get('channelCode', '') or _safe_get(data, 'event', 'channel', 'channelCode', default=''),
        'requestId': _safe_get(data, 'event', 'request', 'id', default='') or rl.get('requestId', ''),
        'clientId': rl.get('clientId', '') or metadata.get('clientId', '') or _safe_get(data, 'event', 'client', 'id', default=''),
    }


def _norm_bot_engine_conversation(hit: dict) -> dict:
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    ev = data.get('event', {})
    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'bot-engine.conversation',
        'tenantName': s.get('tenantName', ''),
        'agentName': s.get('agentName', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': s.get('msg', ''),
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'podName': _safe_get(s, 'kubernetes', 'pod_name', default=''),
        'namespace': _safe_get(s, 'kubernetes', 'namespace_name', default=''),
        'connectionId': _safe_get(ev, 'connection', 'id', default=''),
        'connectionToken': _safe_get(ev, 'connection', 'token', default=''),
        'sessionId': _safe_get(ev, 'session', 'id', default=''),
        'sessionToken': _safe_get(ev, 'session', 'token', default=''),
        'clientId': _safe_get(ev, 'client', 'id', default=''),
        'channelCode': _safe_get(ev, 'channel', 'channelCode', default=''),
        'requestId': _safe_get(ev, 'request', 'id', default=''),
        'actionType': data.get('type', ''),
        'actionSubtype': data.get('subtype', ''),
        'actionText': _safe_get(data, 'action', 'data', 'text', default=''),
    }


def _norm_conversation_per_tenant(hit: dict) -> dict:
    s = hit.get('_source', {})
    ev_obj = s.get('event', {})
    original = ev_obj.get('original', {})
    orig_data = original.get('data', {})
    inner_ev = orig_data.get('event', {})
    context = orig_data.get('context', {})

    inputs_raw = context.get('inputs', [])
    outputs_raw = context.get('outputs', [])
    events_raw = context.get('events', [])

    detail_parts: List[str] = []
    for inp in inputs_raw:
        if isinstance(inp, list) and len(inp) >= 2 and isinstance(inp[1], dict):
            text = _safe_get(inp[1], 'data', 'text', default='')
            if text:
                detail_parts.append(f'Input: {text}')
    for out in outputs_raw:
        if isinstance(out, list) and len(out) >= 2 and isinstance(out[1], dict):
            text = _safe_get(out[1], 'data', 'text', default='')
            if text:
                detail_parts.append(f'Output: {text}')

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'conversation',
        'tenantName': _safe_get(s, 'tenant', 'name', default=original.get('tenantName', '')),
        'agentName': _safe_get(s, 'tenant', 'agent', 'name', default=original.get('agentName', '')),
        'moduleName': ev_obj.get('module', original.get('moduleName', '')),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': s.get('msg', ''),
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'connectionId': _safe_get(s, 'connection', 'id', default=''),
        'connectionToken': _safe_get(s, 'connection', 'token', default=''),
        'sessionId': _safe_get(inner_ev, 'session', 'id', default=''),
        'sessionToken': _safe_get(inner_ev, 'session', 'token', default=''),
        'clientId': _safe_get(inner_ev, 'client', 'id', default=''),
        'channelCode': _safe_get(inner_ev, 'channel', 'channelCode', default=''),
        'requestId': _safe_get(s, 'request', 'id', default=''),
        'category': orig_data.get('category', ''),
        'detail': ' | '.join(detail_parts) if detail_parts else '',
        'inputCount': len(inputs_raw),
        'outputCount': len(outputs_raw),
        'eventCount': len(events_raw),
    }


def _norm_analytics(hit: dict) -> dict:
    s = hit.get('_source', {})
    ev_obj = s.get('event', {})
    original = ev_obj.get('original', {})
    orig_data = original.get('data', {})
    inner_ev = orig_data.get('event', {})
    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'analytics',
        'tenantName': _safe_get(s, 'tenant', 'name', default=original.get('tenantName', '')),
        'agentName': _safe_get(s, 'tenant', 'agent', 'name', default=original.get('agentName', '')),
        'moduleName': ev_obj.get('module', original.get('moduleName', '')),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': s.get('msg', ''),
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'connectionToken': _safe_get(s, 'connection', 'token', default=''),
        'sessionToken': _safe_get(orig_data, 'sessionToken', default=''),
        'channelCode': _safe_get(inner_ev, 'channel', 'channelCode', default=''),
        'eventType': inner_ev.get('type', ''),
        'eventSubtype': inner_ev.get('subtype', ''),
        'category': orig_data.get('category', ''),
    }


def _norm_integration_manager(hit: dict) -> dict:
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    metadata = _safe_get(data, 'context', 'metadata', default={}) or {}
    msg = s.get('msg', '')

    endpoint = ''
    http_status = None
    duration_ms = None
    m = re.match(r'\s*-->\s+(GET|POST|PUT|DELETE|PATCH|HEAD)\s+(\S+)\s+(\d+)\s+(\d+)ms', msg)
    if m:
        endpoint = f'{m.group(1)} {m.group(2)}'
        http_status = int(m.group(3))
        duration_ms = int(m.group(4))

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'integration-manager',
        'tenantName': s.get('tenantName', ''),
        'agentName': s.get('agentName', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': msg,
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'podName': _safe_get(s, 'kubernetes', 'pod_name', default=''),
        'namespace': _safe_get(s, 'kubernetes', 'namespace_name', default=''),
        'connectionId': metadata.get('connectionId', ''),
        'sessionId': metadata.get('sessionId', ''),
        'requestId': metadata.get('requestId', '') or rl.get('requestId', ''),
        'clientId': metadata.get('clientId', '') or rl.get('clientId', ''),
        'channelCode': metadata.get('channelCode', ''),
        'endpoint': endpoint,
        'httpStatus': http_status,
        'durationMs': duration_ms or _safe_get(rl, 'data', 'duration', default=None),
    }


def _norm_stream_server(hit: dict) -> dict:
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    call_data = _safe_get(data, 'call', 'data', default={}) or {}
    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'stream-server',
        'tenantName': s.get('tenantName', '') or call_data.get('tenantName', ''),
        'agentName': s.get('agentName', '') or call_data.get('agentName', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': s.get('level', 30),
        'levelName': LOG_LEVELS.get(s.get('level', 30), 'UNKNOWN'),
        'message': s.get('msg', ''),
        'uuid': s.get('uuid', ''),
        'hostname': s.get('hostname', ''),
        'podName': _safe_get(s, 'kubernetes', 'pod_name', default=''),
        'namespace': _safe_get(s, 'kubernetes', 'namespace_name', default=''),
        'connectionId': call_data.get('connectionId', ''),
        'sessionId': call_data.get('sessionId', ''),
        'requestId': data.get('requestId', ''),
        'clientId': s.get('clientId', '') or call_data.get('clientId', ''),
        'callSid': s.get('callSid', '') or _safe_get(data, 'call', 'callSid', default=''),
        'streamSid': s.get('streamSid', '') or _safe_get(data, 'call', 'streamSid', default=''),
        'contextId': data.get('contextId', ''),
    }


def _norm_nlp_server(hit: dict) -> dict:
    s = hit.get('_source', {})
    metadata = s.get('metadata', {}) or {}
    usage = _safe_get(s, 'result', 'usage', default={}) or {}
    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'nlp-server',
        'tenantName': metadata.get('tenant_name', ''),
        'agentName': metadata.get('agent_name', ''),
        'moduleName': '',
        'level': s.get('level', 30) if isinstance(s.get('level'), int) else 30,
        'levelName': 'INFO',
        'message': '',
        'uuid': '',
        'hostname': '',
        'podName': _safe_get(s, 'kubernetes', 'pod_name', default=''),
        'namespace': _safe_get(s, 'kubernetes', 'namespace_name', default=''),
        'connectionId': metadata.get('connection_id', ''),
        'sessionId': metadata.get('session_id', ''),
        'requestId': metadata.get('request_id', '') or s.get('request_id', ''),
        'clientId': metadata.get('client_id', ''),
        'channelCode': metadata.get('channel_code', ''),
        'inputText': s.get('text', ''),
        'classifiedAction': s.get('action', ''),
        'modelId': _safe_get(s, 'result', 'model_id', default=''),
        'promptTokens': usage.get('prompt_tokens'),
        'completionTokens': usage.get('completion_tokens'),
        'totalTokens': usage.get('total_tokens'),
    }


# ---------------------------------------------------------------------------
# Trace event explosion — one event per input/output/action
# ---------------------------------------------------------------------------


def _explode_conversation_trace(hit: dict) -> List[dict]:
    """Explode a single conversation-* doc into per-input/output trace events."""
    s = hit.get('_source', {})
    ev_obj = s.get('event', {})
    original = ev_obj.get('original', {})
    orig_data = original.get('data', {})
    inner_ev = orig_data.get('event', {})
    context = orig_data.get('context', {})
    doc_ts = s.get('@timestamp', '')
    category = orig_data.get('category', '')

    common = {
        'source': 'conversation',
        'sessionId': _safe_get(inner_ev, 'session', 'id', default=''),
        'sessionToken': _safe_get(inner_ev, 'session', 'token', default=''),
        'connectionId': _safe_get(s, 'connection', 'id', default=''),
        'connectionToken': _safe_get(s, 'connection', 'token', default=''),
        'channelCode': _safe_get(inner_ev, 'channel', 'channelCode', default=''),
        'moduleName': ev_obj.get('module', original.get('moduleName', '')),
        'level': LOG_LEVELS.get(s.get('level', 30), 'INFO'),
        'category': category,
        'requestId': _safe_get(s, 'request', 'id', default=_safe_get(inner_ev, 'request', 'id', default='')),
        'clientId': _safe_get(inner_ev, 'client', 'id', default=''),
    }

    events: List[dict] = []

    for inp in context.get('inputs', []):
        if not isinstance(inp, list) or len(inp) < 2:
            continue
        ts = inp[0] if isinstance(inp[0], str) else doc_ts
        action = inp[1] if isinstance(inp[1], dict) else {}
        name = action.get('name', '')
        text = _safe_get(action, 'data', 'text', default='')
        a_type = action.get('type', '')
        a_subtype = action.get('subtype', '')
        exp_name = _safe_get(action, 'meta', 'experience', 'name', default='')
        type_label = f'{a_type}/{a_subtype}'.strip('/') if (a_type or a_subtype) else ''
        display = text or name or type_label
        if not display:
            continue
        events.append({
            **common,
            'timestamp': ts,
            'eventType': 'INPUT',
            'text': display,
            'actionName': name,
            'experienceName': exp_name,
        })

    for out in context.get('outputs', []):
        if not isinstance(out, list) or len(out) < 2:
            continue
        ts = out[0] if isinstance(out[0], str) else doc_ts
        action = out[1] if isinstance(out[1], dict) else {}
        text = _safe_get(action, 'data', 'text', default='')
        a_type = action.get('type', '')
        a_subtype = action.get('subtype', '')
        name = action.get('name', '')
        exp_name = _safe_get(action, 'meta', 'experience', 'name', default='')
        res_name = _safe_get(action, 'meta', 'resource', 'name', default='')
        type_label = f'{a_type}/{a_subtype}'.strip('/') if (a_type or a_subtype) else ''
        display = text or name or type_label or res_name
        if not display:
            continue
        events.append({
            **common,
            'timestamp': ts,
            'eventType': 'OUTPUT',
            'text': display,
            'experienceName': exp_name,
            'resourceName': res_name,
        })

    if not events:
        msg = s.get('msg', '')
        action_obj = orig_data.get('action', {})
        action_text = _safe_get(action_obj, 'data', 'text', default='')
        action_name = action_obj.get('name', '') or action_obj.get('actionName', '')
        data_type = orig_data.get('type', '')
        data_subtype = orig_data.get('subtype', '')
        type_label = f'{data_type}.{data_subtype}'.strip('.') if (data_type or data_subtype) else ''

        display = msg or action_text or action_name
        if not display and type_label and type_label not in ('action', 'events', 'event'):
            display = type_label

        if display:
            events.append({
                **common,
                'timestamp': doc_ts,
                'eventType': 'EVENT',
                'text': display,
                'experienceName': '',
            })

    return events


def _trace_from_bot_engine(hit: dict) -> dict:
    """Convert a bot-engine.default hit into a trace event."""
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    metadata = data.get('metadata', {})
    level = s.get('level', 30)

    event_type = 'ERROR' if level >= 50 else 'SYSTEM'
    if data.get('apiName'):
        event_type = 'INTEGRATION'

    call_token = s.get('callToken', '') or rl.get('callToken', '')

    msg = s.get('msg', '')
    api_name = data.get('apiName', '')
    method_name = data.get('methodName', '')
    if event_type == 'INTEGRATION' and api_name:
        display = f'{api_name}/{method_name}' if method_name else api_name
        if msg:
            display += f' — {msg}'
    else:
        display = msg or rl.get('moduleName', '')

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'bot-engine',
        'sessionId': metadata.get('sessionId', '') or _safe_get(data, 'event', 'session', 'id', default=''),
        'connectionId': metadata.get('connectionId', '') or _safe_get(data, 'event', 'connection', 'id', default=''),
        'connectionToken': _safe_get(data, 'event', 'connection', 'token', default=call_token),
        'channelCode': metadata.get('channelCode', '') or _safe_get(data, 'event', 'channel', 'channelCode', default=''),
        'requestId': _safe_get(data, 'event', 'request', 'id', default='') or rl.get('requestId', ''),
        'clientId': rl.get('clientId', '') or metadata.get('clientId', '') or _safe_get(data, 'event', 'client', 'id', default=''),
        'moduleName': rl.get('moduleName', ''),
        'level': LOG_LEVELS.get(level, 'INFO'),
        'eventType': event_type,
        'text': display,
        'experienceName': '',
        'apiName': api_name,
        'methodName': method_name,
        'durationMs': data.get('time'),
    }


def _trace_from_integration(hit: dict) -> dict:
    """Convert an integration-manager hit into a trace event."""
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    metadata = _safe_get(data, 'context', 'metadata', default={}) or {}
    msg = s.get('msg', '')

    call_token = s.get('callToken', '') or rl.get('callToken', '')
    api_name = data.get('apiName', '') or rl.get('apiName', '')
    method_name = data.get('methodName', '') or rl.get('methodName', '')

    endpoint = ''
    http_status = None
    duration_ms = None
    m = re.match(r'\s*-->\s+(GET|POST|PUT|DELETE|PATCH|HEAD)\s+(\S+)\s+(\d+)\s+(\d+)ms', msg)
    if m:
        endpoint = f'{m.group(1)} {m.group(2)}'
        http_status = int(m.group(3))
        duration_ms = int(m.group(4))

    label = msg
    if api_name and method_name:
        label = f'{api_name}/{method_name}'
        if endpoint:
            label += f' ({endpoint})'
    elif api_name:
        label = api_name

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'integration-manager',
        'callToken': call_token,
        'sessionId': metadata.get('sessionId', ''),
        'connectionId': metadata.get('connectionId', ''),
        'requestId': metadata.get('requestId', '') or rl.get('requestId', ''),
        'clientId': metadata.get('clientId', '') or rl.get('clientId', ''),
        'channelCode': metadata.get('channelCode', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': LOG_LEVELS.get(s.get('level', 30), 'INFO'),
        'eventType': 'INTEGRATION',
        'text': label,
        'experienceName': '',
        'endpoint': endpoint,
        'httpStatus': http_status,
        'durationMs': duration_ms or data.get('time'),
        'apiName': api_name,
        'methodName': method_name,
    }


def _trace_from_stream_server(hit: dict) -> dict:
    """Convert a stream-server hit into a trace event."""
    s = hit.get('_source', {})
    rl = s.get('rawLog', {})
    data = rl.get('data', {})
    call_data = _safe_get(data, 'call', 'data', default={}) or {}
    level = s.get('level', 30)
    msg = s.get('msg', '')

    error_msg = _safe_get(data, 'error', 'message', default='')
    display = msg
    if error_msg:
        display = f'{msg} — {error_msg}' if msg else error_msg

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'stream-server',
        'sessionId': call_data.get('sessionId', ''),
        'connectionId': call_data.get('connectionId', ''),
        'connectionToken': '',
        'channelCode': '',
        'requestId': data.get('requestId', ''),
        'clientId': s.get('clientId', '') or call_data.get('clientId', ''),
        'moduleName': rl.get('moduleName', ''),
        'level': LOG_LEVELS.get(level, 'INFO'),
        'eventType': 'ERROR' if level >= 50 else 'STREAM',
        'text': display,
        'experienceName': '',
        'contextId': data.get('contextId', ''),
        'durationMs': data.get('time'),
    }


def _trace_from_nlp_server(hit: dict) -> dict:
    """Convert an nlp-server hit into a trace event."""
    s = hit.get('_source', {})
    metadata = s.get('metadata', {}) or {}
    usage = _safe_get(s, 'result', 'usage', default={}) or {}
    input_text = s.get('text', '')
    action = s.get('action', '')
    model_id = _safe_get(s, 'result', 'model_id', default='')
    total_tokens = usage.get('total_tokens', '')

    if not input_text and not action:
        return {}
    display = f'NLP: "{input_text}" → {action}' if input_text else action
    if model_id:
        display += f' [{model_id}]'
    if total_tokens:
        display += f' ({total_tokens} tokens)'

    return {
        'timestamp': s.get('@timestamp', ''),
        'source': 'nlp-server',
        'sessionId': metadata.get('session_id', ''),
        'connectionId': metadata.get('connection_id', ''),
        'connectionToken': '',
        'channelCode': metadata.get('channel_code', ''),
        'requestId': metadata.get('request_id', '') or s.get('request_id', ''),
        'clientId': metadata.get('client_id', ''),
        'moduleName': '',
        'level': 'INFO',
        'eventType': 'NLP',
        'text': display,
        'experienceName': '',
        'inputText': input_text,
        'classifiedAction': action,
    }


def _build_trace_events(results: list, extra_results: Optional[list] = None) -> List[dict]:
    """Build the flat traceEvents list from raw OpenSearch results.

    Uses callToken (= connectionToken) to correlate integration-manager logs
    back to their originating connection/session.

    ``extra_results`` is an optional list of (source_tag, result) tuples from
    the second-pass queries (stream-server, nlp-server).
    """
    trace: List[dict] = []

    # results[0] = bot-engine.default — skip events with no correlation IDs (system noise)
    res = results[0]
    if not isinstance(res, Exception):
        for hit in res.get('hits', {}).get('hits', []):
            try:
                ev = _trace_from_bot_engine(hit)
                if ev.get('connectionId') or ev.get('sessionId') or ev.get('connectionToken'):
                    trace.append(ev)
            except Exception as exc:
                logger.warning('Trace bot-engine error: %s', exc)

    # results[2] = conversation-* — skip events with no text content
    res = results[2]
    if not isinstance(res, Exception):
        for hit in res.get('hits', {}).get('hits', []):
            try:
                evts = _explode_conversation_trace(hit)
                for ev in evts:
                    if ev.get('text'):
                        trace.append(ev)
            except Exception as exc:
                logger.warning('Trace conversation error: %s', exc)

    # Build callToken → (connectionId, sessionId, channelCode) mapping
    # from conversation and bot-engine events that already have these IDs.
    token_map: Dict[str, dict] = {}
    for ev in trace:
        ct = ev.get('connectionToken', '')
        if ct and ev.get('connectionId'):
            if ct not in token_map:
                token_map[ct] = {
                    'connectionId': ev['connectionId'],
                    'sessionId': ev.get('sessionId', ''),
                    'channelCode': ev.get('channelCode', ''),
                }

    # results[4] = integration-manager
    res = results[4]
    if not isinstance(res, Exception):
        for hit in res.get('hits', {}).get('hits', []):
            try:
                ev = _trace_from_integration(hit)
                ct = ev.pop('callToken', '')
                if ct and ct in token_map:
                    mapping = token_map[ct]
                    ev['connectionId'] = ev['connectionId'] or mapping['connectionId']
                    ev['sessionId'] = ev['sessionId'] or mapping['sessionId']
                    ev['channelCode'] = ev['channelCode'] or mapping['channelCode']
                    ev['connectionToken'] = ct
                trace.append(ev)
            except Exception as exc:
                logger.warning('Trace integration error: %s', exc)

    # Second-pass results: stream-server and nlp-server
    for tag, res in (extra_results or []):
        if isinstance(res, Exception):
            continue
        for hit in res.get('hits', {}).get('hits', []):
            try:
                if tag == 'stream-server':
                    ev = _trace_from_stream_server(hit)
                elif tag == 'nlp-server':
                    ev = _trace_from_nlp_server(hit)
                else:
                    continue
                if ev and ev.get('text'):
                    trace.append(ev)
            except Exception as exc:
                logger.warning('Trace %s error: %s', tag, exc)

    trace.sort(key=lambda x: x.get('timestamp', ''))
    return trace


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

_INDEX_META = [
    ('bot-engine.default', _norm_bot_engine_default),
    ('bot-engine.conversation', _norm_bot_engine_conversation),
    ('conversation', _norm_conversation_per_tenant),
    ('analytics', _norm_analytics),
    ('integration-manager', _norm_integration_manager),
]

_EXTRA_INDEX_META = [
    ('stream-server', _norm_stream_server),
    ('nlp-server', _norm_nlp_server),
]


def _build_report(
    logs: List[dict],
    tenant_name: str,
    agent_name: str,
    time_gte: str,
    time_lte: str,
    raw_counts: Dict[str, Any],
    trace_events: Optional[List[dict]] = None,
) -> dict:
    logs.sort(key=lambda x: x.get('timestamp', ''))

    errors = [l for l in logs if l.get('level', 0) >= 50]
    warns = [l for l in logs if l.get('level', 0) == 40]

    channels: set = set()
    sessions: set = set()
    connections: set = set()

    for log in logs:
        ch = log.get('channelCode', '')
        if ch:
            channels.add(ch)
        sid = log.get('sessionId', '') or log.get('sessionToken', '')
        if sid:
            sessions.add(sid)
        cid = log.get('connectionId', '') or log.get('connectionToken', '')
        if cid:
            connections.add(cid)

    error_entries = [
        {
            'timestamp': e['timestamp'],
            'source': e['source'],
            'module': e.get('moduleName', ''),
            'message': e.get('message', '') or e.get('detail', ''),
            'connectionId': e.get('connectionId', ''),
            'sessionId': e.get('sessionId', ''),
        }
        for e in errors
    ]

    timeline: List[dict] = []
    for log in logs:
        entry: Dict[str, Any] = {
            'timestamp': log['timestamp'],
            'source': log['source'],
            'level': log.get('levelName', 'INFO'),
            'module': log.get('moduleName', ''),
        }
        src = log['source']
        if src == 'conversation':
            entry['type'] = log.get('category', 'event')
            entry['detail'] = log.get('detail', '') or log.get('message', '')
            entry['channel'] = log.get('channelCode', '')
        elif src == 'bot-engine.conversation':
            entry['type'] = log.get('actionType', '') or 'conversation_event'
            entry['detail'] = log.get('actionText', '') or log.get('message', '')
            entry['channel'] = log.get('channelCode', '')
        elif src == 'integration-manager':
            entry['type'] = 'integration'
            entry['detail'] = log.get('message', '')
            if log.get('endpoint'):
                entry['endpoint'] = log['endpoint']
                entry['httpStatus'] = log.get('httpStatus')
                entry['durationMs'] = log.get('durationMs')
        elif src == 'analytics':
            entry['type'] = log.get('eventType', 'analytics')
            entry['detail'] = log.get('eventSubtype', '') or log.get('message', '')
            entry['channel'] = log.get('channelCode', '')
        elif src == 'stream-server':
            entry['type'] = 'stream'
            entry['detail'] = log.get('message', '')
            if log.get('contextId'):
                entry['contextId'] = log['contextId']
            if log.get('durationMs') or log.get('callSid'):
                entry['callSid'] = log.get('callSid', '')
        elif src == 'nlp-server':
            entry['type'] = 'nlp'
            entry['detail'] = f'"{log.get("inputText", "")}" → {log.get("classifiedAction", "")}'
            if log.get('modelId'):
                entry['model'] = log['modelId']
            if log.get('totalTokens'):
                entry['tokens'] = log['totalTokens']
        else:
            entry['type'] = 'system'
            entry['detail'] = log.get('message', '')
        timeline.append(entry)

    integrations = [
        {
            'timestamp': l['timestamp'],
            'endpoint': l['endpoint'],
            'status': l.get('httpStatus'),
            'duration_ms': l.get('durationMs'),
        }
        for l in logs
        if l['source'] == 'integration-manager' and l.get('endpoint')
    ]

    return {
        'summary': {
            'tenantName': tenant_name,
            'agentName': agent_name,
            'timeRange': {'from': time_gte, 'to': time_lte},
            'totalLogs': len(logs),
            'errorCount': len(errors),
            'warnCount': len(warns),
            'channelsUsed': sorted(channels),
            'sessionsFound': len(sessions),
            'connectionsFound': len(connections),
        },
        'errors': error_entries,
        'timeline': timeline,
        'integrations': integrations,
        'rawLogCounts': raw_counts,
        'traceEvents': trace_events or [],
    }


# ---------------------------------------------------------------------------
# Main tool entry point
# ---------------------------------------------------------------------------


async def log_correlation_tool(args: LogCorrelationArgs) -> list[dict]:
    """Correlate logs across all index types and return a structured debugging report."""
    try:
        tenant_name = args.tenant_name or ''
        agent_name = args.agent_name or ''
        time_range = args.time_range or 'last 1 hour'
        keyword = args.keyword
        connection_id = args.connection_id
        session_id = args.session_id
        max_results = min(args.max_results_per_index or 50, 100)

        level_filter = LEVEL_NAME_TO_INT.get((args.log_level or '').lower())

        time_gte = ''
        time_lte = 'now'

        # ---- Mode 2: discover tenant/time from connection or session ID ----
        if connection_id or session_id:
            disc_query = (
                _connection_id_query(connection_id)
                if connection_id
                else _session_id_query(session_id)
            )

            disc = await _query_index(args, 'bot-engine.conversation-*', disc_query, 1)
            hits = disc.get('hits', {}).get('hits', [])
            if not hits:
                disc = await _query_index(args, 'conversation-*', disc_query, 1)
                hits = disc.get('hits', {}).get('hits', [])

            if hits:
                src = hits[0].get('_source', {})
                tenant_name = tenant_name or src.get('tenantName', '') or _safe_get(src, 'tenant', 'name', default='')
                agent_name = agent_name or src.get('agentName', '') or _safe_get(src, 'tenant', 'agent', 'name', default='')
                ts = src.get('@timestamp', '')
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        time_gte = (dt - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        time_lte = (dt + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    except Exception:
                        time_gte, time_lte = _parse_time_range('last 1 hour')
                else:
                    time_gte, time_lte = _parse_time_range('last 1 hour')
            else:
                id_label = f'connection_id={connection_id}' if connection_id else f'session_id={session_id}'
                return [{'type': 'text', 'text': f'No logs found for {id_label}. Try providing tenant_name and time_range directly.'}]
        else:
            time_gte, time_lte = _parse_time_range(time_range)

        if not tenant_name:
            return [
                {
                    'type': 'text',
                    'text': 'Error: tenant_name is required (or provide connection_id / session_id to auto-discover).',
                }
            ]

        # ---- Build queries ----
        tq = _tenant_query(tenant_name, time_gte, time_lte, level_filter, keyword)
        ptq = _per_tenant_query(time_gte, time_lte, level_filter, keyword)

        slug = _tenant_to_index_slug(tenant_name)
        conv_idx = f'conversation-{slug}-{agent_name}-*' if agent_name else f'conversation-{slug}-*'
        anl_idx = f'analytics-{slug}-{agent_name}-*' if agent_name else f'analytics-{slug}-*'

        # ---- Pass 1: Parallel fetch across core index types ----
        results = await asyncio.gather(
            _query_index(args, 'bot-engine.default-*', tq, max_results),
            _query_index(args, 'bot-engine.conversation-*', tq, max_results),
            _query_index(args, conv_idx, ptq, max_results),
            _query_index(args, anl_idx, ptq, max_results),
            _query_index(args, 'integration-manager.*', tq, max_results),
            return_exceptions=True,
        )

        # ---- Normalize + merge (core indices) ----
        all_logs: List[dict] = []
        raw_counts: Dict[str, Any] = {}

        for i, (name, normalizer) in enumerate(_INDEX_META):
            res = results[i]
            if isinstance(res, Exception):
                raw_counts[name] = f'error: {res}'
                continue
            hits_obj = res.get('hits', {})
            total = hits_obj.get('total', {}).get('value', 0)
            raw_counts[name] = total
            for hit in hits_obj.get('hits', []):
                try:
                    all_logs.append(normalizer(hit))
                except Exception as exc:
                    logger.warning('Normalizer error for %s: %s', name, exc)

        # ---- Pass 2: Correlate stream-server + nlp-server via IDs ----
        corr_ids = _collect_correlation_ids(all_logs)
        extra_results: List[Tuple[str, Any]] = []
        if corr_ids['connectionIds'] or corr_ids['requestIds'] or corr_ids['sessionIds']:
            pass2_time_query = _time_range_clause(time_gte, time_lte)
            extra_raw = await asyncio.gather(
                _query_by_correlation_ids(
                    args, 'default.stream-server.*', pass2_time_query,
                    corr_ids, 'stream-server', max_results,
                ),
                _query_by_correlation_ids(
                    args, 'default.nlp-server.*', pass2_time_query,
                    corr_ids, 'nlp-server', max_results,
                ),
                return_exceptions=True,
            )
            for j, tag in enumerate(['stream-server', 'nlp-server']):
                res = extra_raw[j]
                if isinstance(res, Exception):
                    raw_counts[tag] = f'error: {res}'
                    continue
                hits_obj = res.get('hits', {})
                total = hits_obj.get('total', {}).get('value', 0)
                raw_counts[tag] = total
                normalizer = _EXTRA_INDEX_META[j][1]
                for hit in hits_obj.get('hits', []):
                    try:
                        all_logs.append(normalizer(hit))
                    except Exception as exc:
                        logger.warning('Normalizer error for %s: %s', tag, exc)
                extra_results.append((tag, res))

        trace_events = _build_trace_events(results, extra_results or None)
        report = _build_report(
            all_logs, tenant_name, agent_name, time_gte, time_lte, raw_counts, trace_events,
        )
        formatted = json.dumps(report, indent=2, default=str)
        return [{'type': 'text', 'text': f'Log Correlation Report:\n{formatted}'}]

    except Exception as exc:
        return log_tool_error('LogCorrelationTool', exc, 'correlating logs')
