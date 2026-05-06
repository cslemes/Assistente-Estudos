"""
Local mock server that mimics the RunPod runsync API.
Routes requests to each worker handler by endpoint_id.
All GPU deps live in one container for local integration testing.

Usage:
    python runpod_workers/mock_server.py

Test:
    curl -X POST http://localhost:8001/v2/embed/runsync \\
      -H "Content-Type: application/json" \\
      -d '{"input": {"text": "redes neurais", "mode": "query"}}'
"""
import importlib

import uvicorn
from fastapi import FastAPI, HTTPException

app = FastAPI(title="RunPod Mock Server")

HANDLERS = {
    "clip": "clip.handler",
    "embed": "embed.handler",
    "ner": "ner.handler",
    "ocr": "ocr.handler",
}


@app.post("/v2/{endpoint_id}/runsync")
async def runsync(endpoint_id: str, body: dict):
    if endpoint_id not in HANDLERS:
        raise HTTPException(status_code=404, detail=f"Unknown endpoint: {endpoint_id}")
    module = importlib.import_module(HANDLERS[endpoint_id])
    try:
        output = module.handler({"input": body["input"]})
        return {"id": "local-test", "status": "COMPLETED", "output": output}
    except Exception as e:
        return {"id": "local-test", "status": "FAILED", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
