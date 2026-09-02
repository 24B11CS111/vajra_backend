from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import uuid

class EmbeddingProvider(ABC):
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        pass

class VectorStore(ABC):
    @abstractmethod
    async def store(self, id: str, embedding: List[float], metadata: Dict[str, Any]):
        pass

    @abstractmethod
    async def search(self, query_embedding: List[float], limit: int) -> List[Dict[str, Any]]:
        pass

class SemanticRetriever(ABC):
    @abstractmethod
    async def retrieve_relevant(self, query: str, limit: int) -> List[Dict[str, Any]]:
        pass

class KnowledgeGraphProvider(ABC):
    @abstractmethod
    async def add_node(self, memory_id: uuid.UUID, data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def add_edge(self, source_node_id: str, target_node_id: str, relationship: str) -> str:
        pass

    @abstractmethod
    async def query_graph(self, query: str) -> Dict[str, Any]:
        pass

class SimilarityEngine(ABC):
    @abstractmethod
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        pass

class MemoryEmbeddingService(ABC):
    @abstractmethod
    async def embed_memory(self, memory_id: uuid.UUID, text: str):
        pass
