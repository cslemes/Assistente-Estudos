import httpx


class RunPodClient:
    def __init__(self, settings):
        self._api_key = settings.runpod_api_key
        self._timeout = settings.runpod_timeout
        self._base_url = settings.runpod_base_url

    def call(self, endpoint_id: str, payload: dict) -> dict:
        url = f"{self._base_url}/{endpoint_id}/runsync"
        with httpx.Client(timeout=self._timeout) as c:
            resp = c.post(
                url,
                json={"input": payload},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") != "COMPLETED":
            raise RuntimeError(
                f"RunPod {body.get('id')}: {body.get('status')} — {body.get('error')}"
            )
        return body["output"]
