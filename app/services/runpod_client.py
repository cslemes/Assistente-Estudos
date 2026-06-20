import runpod as _runpod


class RunPodClient:
    def __init__(self, settings):
        _runpod.api_key = settings.runpod_api_key
        self._timeout = settings.runpod_timeout

    def call(self, endpoint_id: str, payload: dict) -> dict:
        endpoint = _runpod.Endpoint(endpoint_id)
        return endpoint.run_sync({"input": payload}, timeout=self._timeout)
