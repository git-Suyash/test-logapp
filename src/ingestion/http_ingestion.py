import threading

import uvicorn
from fastapi import FastAPI, Request, Response

from observability.logging_config import setup_logger
from observability.metrics import QUEUE_SIZE
from pipeline.queues import raw_queue

logger = setup_logger()

app = FastAPI(title="LogApp HTTP Ingestion", docs_url="/docs")


@app.post("/ingest", status_code=202)
async def ingest(request: Request):
    """Accept raw log lines via HTTP.

    Supports two content types:
    - text/plain: each newline-delimited line becomes one log event
    - application/json: {"log": "..."} or {"logs": ["...", "..."]}
    """
    content_type = request.headers.get("content-type", "")
    body_bytes = await request.body()

    if "application/json" in content_type:
        import json as _json
        try:
            payload = _json.loads(body_bytes)
        except Exception:
            return Response(
                content='{"error": "invalid JSON"}',
                status_code=400,
                media_type="application/json",
            )
        if isinstance(payload, list):
            lines = [str(x) for x in payload]
        elif isinstance(payload, dict):
            if "logs" in payload:
                lines = [str(x) for x in payload["logs"]]
            elif "log" in payload:
                lines = [str(payload["log"])]
            else:
                lines = [_json.dumps(payload)]
        else:
            lines = [str(payload)]
    else:
        text = body_bytes.decode("utf-8", errors="replace")
        lines = text.splitlines()

    queued = 0
    for line in lines:
        line = line.strip()
        if line:
            raw_queue.put(line)
            queued += 1

    QUEUE_SIZE.set(raw_queue.qsize())
    logger.info("HTTP ingestion: queued %d log(s)", queued)
    return {"queued": queued, "queue_size": raw_queue.qsize()}


@app.get("/health")
async def health():
    return {"status": "ok", "queue_size": raw_queue.qsize()}


def start_http_ingestion(host: str = "0.0.0.0", port: int = 8001) -> None:
    def _run() -> None:
        uvicorn.run(app, host=host, port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True, name="http-ingestion")
    thread.start()
    logger.info("HTTP ingestion server started at http://%s:%d", host, port)
