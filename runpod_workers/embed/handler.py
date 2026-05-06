# RunPod serverless worker for text embedding
# Input: {"text": str, "mode": "query" | "passage"}
# Output: {"dense": [...], "sparse": {"indices": [...], "values": [...]}, "colbert": [...]}
import os
from functools import lru_cache

if "TOKENIZERS_PARALLELISM" not in os.environ:
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

@lru_cache(maxsize=1)
def _get_models():
    from fastembed import TextEmbedding
    from fastembed.sparse.bm25 import Bm25
    from fastembed.late_interaction import LateInteractionTextEmbedding
    dense = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    bm25 = Bm25("Qdrant/bm25")
    colbert = LateInteractionTextEmbedding("colbert-ir/colbertv2.0")
    return dense, bm25, colbert

def handler(event):
    inp = event["input"]
    text = inp["text"]
    mode = inp.get("mode", "passage")
    dense_model, bm25_model, colbert_model = _get_models()
    embed_fn = "embed" if mode == "query" else "passage_embed"
    dense = list(getattr(dense_model, embed_fn)([text]))[0].tolist()
    sparse = list(getattr(bm25_model, embed_fn)([text]))[0].as_object()
    colbert = list(getattr(colbert_model, embed_fn)([text]))[0].tolist()
    return {"dense": dense, "sparse": sparse, "colbert": colbert}

if __name__ == "__main__":
    import runpod
    runpod.serverless.start({"handler": handler})
