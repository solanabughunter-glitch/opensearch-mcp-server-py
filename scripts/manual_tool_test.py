import os, sys, json, asyncio
from pathlib import Path

# Make "src" importable regardless of where we run this script
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / 'src'))

from tools.tool_params import AggregationsArgs
from tools.tools import aggregations_tool


async def main():
    # NOTE: if you didn't map status as keyword, change "status" -> "status.keyword"
    args = AggregationsArgs(
        index='logs',
        aggs={'by_status': {'terms': {'field': 'status', 'size': 5}}},
        query=None,
        timeout='5s',
        track_total_hits=False,
        raw=False,  # trimmed first
    )

    # point to your local OpenSearch (security disabled)
    os.environ.setdefault('OPENSEARCH_URL', 'http://localhost:9200')

    print('Running AggregationsTool (trimmed)...')
    out = await aggregations_tool(args)
    print(out[0]['text'])

    print('\nRunning AggregationsTool (raw)...')
    args.raw = True
    out_raw = await aggregations_tool(args)
    print(out_raw[0]['text'])


if __name__ == '__main__':
    asyncio.run(main())
