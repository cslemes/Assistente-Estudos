# RunPod serverless worker for Portuguese NER
# Input: {"text": str}
# Output: {"entities": {"PER": [...], "ORG": [...], ...}}
from functools import lru_cache

NER_MODEL_ID = "lfcc/bert-portuguese-ner"
MIN_ENTITY_CONFIDENCE = 0.80

@lru_cache(maxsize=1)
def _get_pipeline():
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    device = 0 if torch.cuda.is_available() else -1
    tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_ID)
    model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_ID)
    return pipeline("ner", model=model, tokenizer=tokenizer,
                    aggregation_strategy="first", device=device)

async def handler(job):
    text = job["input"]["text"]
    if len(text) > 5000:
        text = text[:5000]
    ner_pipeline = _get_pipeline()
    raw = ner_pipeline(text)
    entities: dict[str, set] = {}
    for ent in raw:
        if len(ent["word"]) < 2 and not ent["word"].isupper():
            continue
        if ent.get("score", 0) < MIN_ENTITY_CONFIDENCE:
            continue
        entities.setdefault(ent["entity_group"], set()).add(ent["word"])
    return {"entities": {k: list(v) for k, v in entities.items()}}

if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
