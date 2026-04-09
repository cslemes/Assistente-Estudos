import json
import os
import urllib.error
import urllib.request


API_BASE_URL = os.getenv("ASSISTENTE_API_URL", "http://127.0.0.1:8000")


def _api_request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=f"{API_BASE_URL}{path}",
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API error {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to API at {API_BASE_URL}. Start it with: uv run uvicorn api:app --reload"
        ) from exc


def main():
    print(f"Calling API: {API_BASE_URL}/sync?background=false")
    result = _api_request("POST", "/sync?background=false")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
