# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""Lightweight FastAPI server that exposes the LogCorrelationTool as a web UI."""

import json
import os
import uvicorn
from .log_correlation import log_correlation_tool
from .tool_params import LogCorrelationArgs
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Optional


app = FastAPI(title="Log Correlation UI")

HTML_PATH = Path(__file__).parent / "log_correlation_ui.html"


class CorrelateRequest(BaseModel):
    """Request body mirroring LogCorrelationArgs (without opensearch_cluster_name)."""

    tenant_name: Optional[str] = None
    agent_name: Optional[str] = None
    time_range: Optional[str] = "last 1 hour"
    log_level: Optional[str] = None
    keyword: Optional[str] = None
    connection_id: Optional[str] = None
    session_id: Optional[str] = None
    max_results_per_index: Optional[int] = 100


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the single-page HTML UI."""
    return HTMLResponse(content=HTML_PATH.read_text(encoding="utf-8"))


@app.post("/api/correlate")
async def correlate(req: CorrelateRequest):
    """Run log correlation and return the structured report."""
    args = LogCorrelationArgs(
        opensearch_cluster_name="",
        tenant_name=req.tenant_name,
        agent_name=req.agent_name,
        time_range=req.time_range,
        log_level=req.log_level,
        keyword=req.keyword,
        connection_id=req.connection_id,
        session_id=req.session_id,
        max_results_per_index=req.max_results_per_index,
    )
    result = await log_correlation_tool(args)
    text = result[0].get("text", "")
    prefix = "Log Correlation Report:\n"
    if text.startswith(prefix):
        text = text[len(prefix):]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": text}


def main():
    """Entry point for ``python -m tools.log_correlation_server``."""
    from mcp_server_opensearch.global_state import set_mode

    set_mode("single")

    host = os.getenv("LOG_CORRELATION_HOST", "127.0.0.1")
    port = int(os.getenv("LOG_CORRELATION_PORT", "8765"))
    print(f"Starting Log Correlation UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
