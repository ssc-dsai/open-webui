from typing import Optional

from qdrant_client import QdrantClient as Client
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from qdrant_client.models import models

from open_webui.apps.retrieval.vector.main import VectorItem, SearchResult, GetResult
from open_webui.config import (
    QDRANT_API_KEY,
    QDRANT_TIMEOUT_SECONDS,
    QDRANT_URL,
)

NO_LIMIT = 999999999


class QdrantClient:
    def __init__(self):
        self.collection_prefix = "open-webui"
        self.client = Client(
            url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=int(QDRANT_TIMEOUT_SECONDS)
        )

    def _result_to_get_result(self, points) -> GetResult:
        ids, documents, metadatas = [], [], []

        for point in points:
            ids.append(point.id)
            documents.append(point.payload["text"])
            metadatas.append(point.payload["metadata"])

        return GetResult(ids=[ids], documents=[documents], metadatas=[metadatas])

    def _result_to_search_result(self, points) -> SearchResult:
        ids, distances, documents, metadatas = [], [], [], []

        for point in points:
            ids.append(point.id)
            distances.append(point.score)
            documents.append(point.payload["text"])
            metadatas.append(point.payload["metadata"])

        return SearchResult(
            ids=[ids], distances=[distances], documents=[documents], metadatas=[metadatas]
        )

    def _create_collection_if_not_exists(self, collection_name: str, dimension: int):
        prefixed_name = f"{self.collection_prefix}_{collection_name}"
        if not self.client.collection_exists(prefixed_name):
            self.client.create_collection(
                collection_name=prefixed_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(
                        comparator=models.MultiVectorComparator.MAX_SIM
                    ),
                ),
            )

    def _create_points(self, items: list[VectorItem]):
        return [
            PointStruct(
                id=item["id"],
                vector=item["vector"],
                payload={"text": item["text"], "metadata": item["metadata"]},
            )
            for item in items
        ]

    def has_collection(self, collection_name: str) -> bool:
        return self.client.collection_exists(f"{self.collection_prefix}_{collection_name}")

    def delete_collection(self, collection_name: str):
        return self.client.delete_collection(f"{self.collection_prefix}_{collection_name}")

    def search(
        self, collection_name: str, vectors: list[list[float | int]], limit: int
    ) -> Optional[SearchResult]:
        limit = limit or NO_LIMIT
        prefixed_name = f"{self.collection_prefix}_{collection_name}"
        query_response = self.client.query_points(
            collection_name=prefixed_name,
            query=vectors[0],
            limit=limit,
            with_payload=True,
        )
        return self._result_to_search_result(query_response.points)

    def query(
        self, collection_name: str, filter: dict, limit: Optional[int] = None
    ) -> Optional[GetResult]:
        if not self.has_collection(collection_name):
            return None
        
        try:
            limit = limit or NO_LIMIT
            field_conditions = [
                FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                for key, value in filter.items()
            ]
            
            prefixed_name = f"{self.collection_prefix}_{collection_name}"
            query_response = self.client.query_points(
                collection_name=prefixed_name,
                query_filter=Filter(must=field_conditions),
                limit=limit,
            )
            return self._result_to_get_result(query_response.points)
        except Exception as e:
            print(f"Error querying Qdrant: {e}")
            return None

    def get(self, collection_name: str) -> Optional[GetResult]:
        prefixed_name = f"{self.collection_prefix}_{collection_name}"
        points = self.client.query_points(
            collection_name=prefixed_name,
            limit=NO_LIMIT,
            with_payload=True,
        )
        return self._result_to_get_result(points.points)

    def insert(self, collection_name: str, items: list[VectorItem]):
        self.upsert(collection_name, items)

    def upsert(self, collection_name: str, items: list[VectorItem]):
        self._create_collection_if_not_exists(collection_name, len(items[0]["vector"]))
        points = self._create_points(items)
        prefixed_name = f"{self.collection_prefix}_{collection_name}"
        return self.client.upsert(prefixed_name, points)

    def delete(
        self,
        collection_name: str,
        ids: Optional[list[str]] = None,
        filter: Optional[dict] = None,
    ):
        field_conditions = [
            FieldCondition(
                key="metadata.id",
                match=MatchValue(value=id_value),
            )
            for id_value in ids
        ] if ids else [
            FieldCondition(
                key=f"metadata.{key}",
                match=MatchValue(value=value),
            )
            for key, value in filter.items()
        ]

        return self.client.delete(
            collection_name=f"{self.collection_prefix}_{collection_name}",
            points_selector=Filter(must=field_conditions),
        )

    def reset(self):
        for collection in self.client.get_collections().collections:
            if collection.name.startswith(self.collection_prefix):
                self.client.delete_collection(collection_name=collection.name)