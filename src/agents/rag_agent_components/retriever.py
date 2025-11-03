from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from config.settings import Config
from logger import housing_logger as logger


class Retriever:
    """Component for retrieving relevant documents from ChromaDB vector store"""

    def __init__(self):
        self.vector_store_path = Config.CHROMA_DB_PATH
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL)
        self.vectorstore = None
        self._initialize_retriever()

    def _initialize_retriever(self):
        """Initialize the vector store retriever"""
        try:
            # Check if vector store exists and has data
            import os
            if not os.path.exists(self.vector_store_path):
                raise FileNotFoundError(f"Vector store directory not found: {self.vector_store_path}")

            self.vectorstore = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings
            )

            # Validate vector store has documents
            try:
                doc_count = self.vectorstore._collection.count()
                if doc_count == 0:
                    logger.warning("Vector store exists but contains no documents")
                else:
                    logger.info(f"Retriever initialized successfully with {doc_count} documents")
            except Exception as count_error:
                logger.warning(f"Could not count documents in vector store: {count_error}")
                logger.info("Retriever initialized successfully (document count unknown)")

        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise

    def retrieve(self, query: str, k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None, search_type: str = "vector") -> Optional[List[Document]]:
        """
        Retrieve top-k relevant documents for the query with optional metadata filtering and search type

        Args:
            query: User query string
            k: Number of documents to retrieve
            metadata_filter: Optional dict of metadata filters (e.g., {"estate": "Tseung Kwan O"})
            search_type: "vector" for semantic search, "keyword" for BM25, "hybrid" for combined

        Returns:
            List of relevant documents, or None if failed
        """
        try:
            if not self.vectorstore:
                logger.error("Retriever not initialized")
                return None

            if search_type == "keyword":
                docs = self._keyword_search(query, k, metadata_filter)
            elif search_type == "hybrid":
                docs = self._hybrid_search(query, k, metadata_filter)
            else:  # default to vector search
                docs = self._vector_search(query, k, metadata_filter)

            logger.info(f"Retrieved {len(docs)} documents using {search_type} search for query: {query[:50]}...")
            return docs

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return None

    def _vector_search(self, query: str, k: int, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Perform vector similarity search"""
        if metadata_filter:
            # Use ChromaDB's native filtering
            try:
                results = self.vectorstore.similarity_search(query, k=k, filter=metadata_filter)
                return results
            except Exception as e:
                logger.warning(f"Native filtering failed, falling back to manual filtering: {e}")
                # Fallback to manual filtering
                all_docs = self.vectorstore.similarity_search(query, k=k*3)
                filtered_docs = []
                for doc in all_docs:
                    if all(doc.metadata.get(key) == value for key, value in metadata_filter.items()):
                        filtered_docs.append(doc)
                        if len(filtered_docs) >= k:
                            break
                return filtered_docs
        else:
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
            return retriever.invoke(query)

    def _keyword_search(self, query: str, k: int, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Perform keyword-based search using BM25"""
        try:
            # Use ChromaDB's native filtering if available
            if metadata_filter:
                results = self.vectorstore.get(where=metadata_filter, limit=10000)
                all_docs = results["documents"]
                metadatas = results["metadatas"]
            else:
                # Get all documents from vector store
                all_docs = self.vectorstore.get(limit=10000)["documents"]
                metadatas = self.vectorstore.get(limit=10000)["metadatas"]

            # Simple keyword matching (in production, use proper BM25 library)
            query_terms = query.lower().split()
            scored_docs = []

            for i, doc_text in enumerate(all_docs):
                metadata = metadatas[i] if metadatas else {}

                # Simple term frequency scoring
                score = sum(1 for term in query_terms if term in doc_text.lower())
                if score > 0:
                    scored_docs.append((score, Document(page_content=doc_text, metadata=metadata)))

            # Sort by score and return top k
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for score, doc in scored_docs[:k]]

        except Exception as e:
            logger.warning(f"Keyword search failed, falling back to vector search: {e}")
            return self._vector_search(query, k, metadata_filter)

    def _hybrid_search(self, query: str, k: int, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Perform hybrid search combining vector and keyword results"""
        try:
            # Get results from both searches
            vector_docs = self._vector_search(query, k, metadata_filter)
            keyword_docs = self._keyword_search(query, k, metadata_filter)

            # Combine and deduplicate based on content similarity
            combined_docs = []
            seen_contents = set()

            # Add vector results first (higher weight)
            for doc in vector_docs:
                content_hash = hash(doc.page_content[:100])  # Simple deduplication
                if content_hash not in seen_contents:
                    combined_docs.append(doc)
                    seen_contents.add(content_hash)

            # Add keyword results if not already included
            for doc in keyword_docs:
                content_hash = hash(doc.page_content[:100])
                if content_hash not in seen_contents:
                    combined_docs.append(doc)
                    seen_contents.add(content_hash)

            return combined_docs[:k]

        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to vector search: {e}")
            return self._vector_search(query, k, metadata_filter)