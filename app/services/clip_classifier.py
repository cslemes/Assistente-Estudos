import logging
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

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
        self.device = device
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(device).eval()

        # Pre-encode label text embeddings once at init
        with torch.no_grad():
            inputs = self.processor(text=self.PROMPTS, return_tensors="pt", padding=True).to(device)
            text_emb = self.model.get_text_features(**inputs)
            self.text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)

        logger.info("CLIP classifier loaded: %s on %s", model_name, device)

    def classify_frame(self, frame_path: str) -> dict:
        image = Image.open(frame_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            img_emb = self.model.get_image_features(**inputs)
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
            probs = (img_emb @ self.text_emb.T).softmax(dim=-1)[0]

        best = int(probs.argmax())
        return {
            "classification": self.LABELS[best],
            "confidence": round(float(probs[best]), 4),
            "scores": {label: round(float(probs[i]), 4) for i, label in enumerate(self.LABELS)},
        }

    def classify_directory(self, frames_dir: str) -> list[dict]:
        frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
        results = []
        for f in frames:
            try:
                r = self.classify_frame(str(f))
                results.append({"frame": f.name, "frame_path": str(f), **r})
            except Exception as e:
                logger.error("Failed to classify %s: %s", f.name, e)
        return results
