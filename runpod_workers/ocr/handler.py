# RunPod serverless worker for EasyOCR (Portuguese + English)
# Input: {"image_b64": str}  (base64-encoded image bytes)
# Output: {"text": str}
import base64
import tempfile
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_reader():
    import easyocr
    return easyocr.Reader(["pt", "en"], gpu=True)

def handler(event):
    image_b64 = event["input"]["image_b64"]
    image_bytes = base64.b64decode(image_b64)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(image_bytes)
        tmp_path = f.name
    reader = _get_reader()
    results = reader.readtext(tmp_path, detail=1)
    text = " ".join(t for _, t, _ in results)
    return {"text": text}

if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
