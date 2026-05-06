import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class CLIPFrameClassifier:
    LABELS = ["slide", "notebook", "whiteboard", "camera"]

    PROMPTS = [
        "a photo of a presentation slide with text and bullet points",
        "a photo of a Jupyter notebook or code editor displayed on a screen",
        "a photo of a whiteboard with handwritten notes or diagrams",
        "a photo of a person speaking or a video camera view of the room",
    ]

    def __init__(self, model_name: str, device: str):
        import torch
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self._Image = Image
        self.device = device
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(device).eval()

        with torch.no_grad():
            inputs = self.processor(text=self.PROMPTS, return_tensors="pt", padding=True).to(device)
            text_out = self.model.text_model(**inputs)
            text_emb = self.model.text_projection(text_out.pooler_output)
            self.text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)

        logger.info("CLIP classifier loaded: %s on %s", model_name, device)

    def classify_frame(self, frame_path: str) -> dict:
        image = self._Image.open(frame_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with self._torch.no_grad():
            vision_out = self.model.vision_model(pixel_values=inputs["pixel_values"])
            img_emb = self.model.visual_projection(vision_out.pooler_output)
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
            probs = (img_emb @ self.text_emb.T).softmax(dim=-1)[0]

        best = int(probs.argmax())
        return {
            "classification": self.LABELS[best],
            "confidence": round(float(probs[best]), 4),
            "scores": {label: round(float(probs[i]), 4) for i, label in enumerate(self.LABELS)},
        }

    def classify_directory(self, frames_dir: str) -> list[dict]:
        from tqdm import tqdm

        frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
        results = []
        for f in tqdm(frames, desc=Path(frames_dir).name, unit="frame"):
            try:
                r = self.classify_frame(str(f))
                results.append({"frame": f.name, "frame_path": str(f), **r})
            except Exception as e:
                logger.error("Failed to classify %s: %s", f.name, e)
        return results


@lru_cache(maxsize=1)
def get_classifier() -> "CLIPFrameClassifier":
    import torch
    from app.config.settings import Settings
    settings = Settings()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if settings.clip_device != "auto":
        device = settings.clip_device
    return CLIPFrameClassifier(settings.clip_model_name, device)


def classify_frame_via_runpod(frame_path: str, client, endpoint_id: str) -> dict:
    import base64
    with open(frame_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    return client.call(endpoint_id, {"op": "classify_frame", "image_b64": image_b64})


def embed_image_via_runpod(image_path: str, client, endpoint_id: str) -> list:
    import base64
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    return client.call(endpoint_id, {"op": "embed_image", "image_b64": image_b64})["embedding"]


def classify_directory_runpod(frames_dir: str, client, endpoint_id: str) -> list:
    from tqdm import tqdm
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    results = []
    for f in tqdm(frames, desc=Path(frames_dir).name, unit="frame"):
        try:
            r = classify_frame_via_runpod(str(f), client, endpoint_id)
            results.append({"frame": f.name, "frame_path": str(f), **r})
        except Exception as e:
            logger.error("RunPod CLIP failed for %s: %s", f.name, e)
    return results
