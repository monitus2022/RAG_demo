from typing import Optional, Dict, Any
from langchain_chroma import Chroma
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from llm_connector import get_llm
from config.settings import Config
from logger import housing_logger as logger


class RAGAgent:
    """RAG Agent for retrieving and answering questions from HK housing estate wiki text using ChromaDB"""

    def __init__(self):
        self.vector_store_path = Config.CHROMA_DB_PATH
        self.llm = get_llm()
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL)
        self.vectorstore = None
        self.qa_chain = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the vector store and QA chain"""
        try:
            # Load persisted ChromaDB vector store
            self.vectorstore = Chroma(
                persist_directory=self.vector_store_path,
                embedding_function=self.embeddings
            )

            # Create retrieval QA chain using LCEL
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

            template = """Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.

            {context}

            Question: {question}
            Answer:"""

            prompt = PromptTemplate.from_template(template)

            self.qa_chain = (
                {"context": retriever | self._format_docs, "question": RunnablePassthrough()}
                | prompt
                | self.llm
            )

            logger.info("RAG Agent initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG Agent: {e}")
            raise

    def _format_docs(self, docs):
        """Format documents for the prompt"""
        return "\n\n".join(doc.page_content for doc in docs)

    def query(self, user_query: str) -> Optional[str]:
        """
        Answer a question using RAG retrieval from wiki text

        Args:
            user_query: Natural language question about HK housing estates

        Returns:
            Answer as formatted string, or None if failed
        """
        try:
            if not self.qa_chain:
                logger.error("RAG Agent not initialized")
                return None

            # Execute the query
            result = self.qa_chain.invoke(user_query)

            logger.info(f"RAG Query executed successfully: {user_query[:50]}...")
            return result

        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return f"Error executing RAG query: {str(e)}"


# Global RAG agent instance
rag_agent = None


def get_rag_agent() -> RAGAgent:
    """Get or create the global RAG agent instance"""
    global rag_agent
    if rag_agent is None:
        rag_agent = RAGAgent()
    return rag_agent


# LangGraph-compatible function for RAG agent node using custom pipeline
def rag_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for RAG agent processing using custom component pipeline

    Args:
        state: Current graph state with user_query and other fields

    Returns:
        Updated state with rag_result
    """
    user_query = state.get("user_query", "")
    conversation_history = state.get("conversation_history", [])
    if not user_query:
        logger.warning("No user query provided to RAG agent")
        return {"rag_result": None}

    try:
        # Import components
        from rag_agent_components.retriever import Retriever
        from rag_agent_components.response_generator import ResponseGenerator

        logger.info(f"Processing RAG query: {user_query}")

        # Enhance query with conversation context if available
        enhanced_query = user_query
        if conversation_history:
            # Add recent context to improve retrieval
            recent_context = " ".join([msg.get("content", "") for msg in conversation_history[-3:]])  # Last 3 messages
            enhanced_query = f"{recent_context} {user_query}".strip()

        # Step 1: Retrieve relevant documents
        retriever = Retriever()

        # Detect estate names in query and use metadata filtering if found
        metadata_filter = _detect_estate_in_query(user_query)
        search_type = "hybrid" if metadata_filter else "vector"  # Use hybrid search for estate queries

        retrieved_docs = retriever.retrieve(enhanced_query, metadata_filter=metadata_filter, search_type=search_type)
        if not retrieved_docs:
            error_msg = "No relevant documents found"
            logger.warning(error_msg)
            return {"rag_result": error_msg}

        # Step 2: Generate response with conversation context
        response_generator = ResponseGenerator()
        response = response_generator.generate_response(user_query, retrieved_docs)

        final_result = response.get('answer', 'No answer generated')
        confidence = response.get('confidence', 0.5)

        # Update conversation history
        updated_history = conversation_history + [
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": final_result, "confidence": confidence}
        ]

        logger.info("RAG agent processing completed successfully")
        return {
            "rag_result": final_result,
            "rag_confidence": confidence,
            "conversation_history": updated_history
        }

    except Exception as e:
        error_msg = f"RAG agent processing failed: {str(e)}"
        logger.error(error_msg)
        return {"rag_result": error_msg}


def _detect_estate_in_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Detect estate names in user query and return metadata filter

    Args:
        query: User query string

    Returns:
        Metadata filter dict if estate found, None otherwise
    """
    try:
        # Get list of all estates from retriever (this could be cached for performance)
        from rag_agent_components.retriever import Retriever
        retriever = Retriever()

        # Get all estate names from vector store metadata
        all_docs = retriever.vectorstore.get(limit=1000)
        estates = set()
        for metadata in all_docs.get('metadatas', []):
            if metadata and 'estate' in metadata:
                estates.add(metadata['estate'])

        # Check if any estate name appears in the query
        for estate in estates:
            if estate in query:
                logger.info(f"Detected estate '{estate}' in query, using metadata filtering")
                return {"estate": estate}

        return None

    except Exception as e:
        logger.warning(f"Estate detection failed: {e}")
        return None