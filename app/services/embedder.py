import os
from app.models.embeddings import QueryEmbeddings, SparseVector


class QueryEmbedder:
    def __init__(self, dense_model_name: str, bm25_model_name: str, late_interaction_model_name: str):
        if "TOKENIZERS_PARALLELISM" not in os.environ:
            os.environ["TOKENIZERS_PARALLELISM"] = "false"

        from fastembed import TextEmbedding
        from fastembed.sparse.bm25 import Bm25
        from fastembed.late_interaction import LateInteractionTextEmbedding

        self.dense_embedding_model = TextEmbedding(dense_model_name)
        self.bm25_embedding_model = Bm25(bm25_model_name)
        self.late_interaction_model = LateInteractionTextEmbedding(late_interaction_model_name)

    def embed_query(self, query: str) -> QueryEmbeddings:
        dense_vector = next(self.dense_embedding_model.embed(query)).tolist()
        sparse_vector = next(self.bm25_embedding_model.embed(query))
        late_vector = next(self.late_interaction_model.embed(query)).tolist()

        return QueryEmbeddings(
            dense=dense_vector,
            sparse_bm25=SparseVector(**sparse_vector.as_object()),
            late=late_vector,
        )


class RunPodQueryEmbedder:
    def __init__(self, settings):
        from app.services.runpod_client import RunPodClient
        self._client = RunPodClient(settings)
        self._endpoint_id = settings.runpod_embed_endpoint_id

    def embed_query(self, query: str) -> "QueryEmbeddings":
        result = self._client.call(self._endpoint_id, {"text": query, "mode": "query"})
        sparse = result["sparse"]
        return QueryEmbeddings(
            dense=result["dense"],
            sparse_bm25=SparseVector(indices=sparse["indices"], values=sparse["values"]),
            late=result["colbert"],
        )


def get_embedder_for_settings(settings) -> "QueryEmbedder | RunPodQueryEmbedder":
    if settings.use_runpod:
        return RunPodQueryEmbedder(settings)
    return QueryEmbedder(
        dense_model_name=settings.dense_model_name,
        bm25_model_name=settings.bm25_model_name,
        late_interaction_model_name=settings.late_interaction_model_name,
    )
