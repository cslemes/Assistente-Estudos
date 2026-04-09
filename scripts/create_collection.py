import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

COLLECTION_NAME = os.getenv("COLLECTION_NAME", "aulas")


def create_collection(collection_name: str = COLLECTION_NAME):
    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )
    
    # Verifica se a collection já existe e remove se necessário
    collections = qdrant.get_collections().collections
    collection_names = [collection.name for collection in collections]
    if COLLECTION_NAME in collection_names:
        print(f"Collection '{COLLECTION_NAME}' já existe. Removendo...")
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
            "colbertv2.0": models.VectorParams(
                size=128,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
            ),
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    print(f"Collection '{collection_name}' created.")


if __name__ == "__main__":
    create_collection()
