# RunPod serverless worker for CLIP frame classification and image embedding
# Input: {"op": "classify_frame" | "embed_image", "image_b64": str}
# Output for classify_frame: {"classification": str, "confidence": float, "scores": dict}
# Output for embed_image: {"embedding": [...]}
import base64
import tempfile
from functools import lru_cache

MODEL_NAME = "openai/clip-vit-base-patch16"
LABELS = ["slide", "notebook", "whiteboard", "camera"]
PROMPTS = [
    "a photo of a presentation slide with text and bullet points",
    "a photo of a Jupyter notebook or code editor displayed on a screen",
    "a photo of a whiteboard with handwritten notes or diagrams",
    "a photo of a person speaking or a video camera view of the room",
]

@lru_cache(maxsize=1)
def _get_model():
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model = CLIPModel.from_pretrained(MODEL_NAME).to(device).eval()
    with torch.no_grad():
        inputs = processor(text=PROMPTS, return_tensors="pt", padding=True).to(device)
        text_out = model.text_model(**inputs)
        text_emb = model.text_projection(text_out.pooler_output)
        text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)
    return model, processor, text_emb, device

def _load_image(image_b64: str, tmp_dir: str):
    from PIL import Image
    image_bytes = base64.b64decode(image_b64)
    path = tmp_dir + "/img.jpg"
    with open(path, "wb") as f:
        f.write(image_bytes)
    return Image.open(path).convert("RGB")

def handler(event):
    import torch, tempfile
    inp = event["input"]
    op = inp["op"]
    model, processor, text_emb, device = _get_model()
    with tempfile.TemporaryDirectory() as tmp_dir:
        image = _load_image(inp["image_b64"], tmp_dir)
        inputs = processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            vision_out = model.vision_model(pixel_values=inputs["pixel_values"])
            img_emb = model.visual_projection(vision_out.pooler_output)
            img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
        if op == "classify_frame":
            probs = (img_emb @ text_emb.T).softmax(dim=-1)[0]
            best = int(probs.argmax())
            return {
                "classification": LABELS[best],
                "confidence": round(float(probs[best]), 4),
                "scores": {label: round(float(probs[i]), 4) for i, label in enumerate(LABELS)},
            }
        elif op == "embed_image":
            return {"embedding": img_emb[0].tolist()}
        else:
            raise ValueError(f"Unknown op: {op}")

if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
