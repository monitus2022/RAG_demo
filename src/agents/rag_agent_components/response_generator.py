from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from llm_connector import get_llm
from logger import housing_logger as logger
from prompts.rag_agent_prompts import RAG_RESPONSE_PROMPT


class ResponseGenerator:
    """Component for generating responses from retrieved documents"""

    def __init__(self):
        self.llm = get_llm()
        self.prompt_template = PromptTemplate.from_template(RAG_RESPONSE_PROMPT)
        self.chain = None
        self._initialize_chain()

    def _initialize_chain(self):
        """Initialize the response generation chain"""
        try:
            self.chain = (
                {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
                | self.prompt_template
                | self.llm
                | StrOutputParser()
            )
            logger.info("Response generator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize response generator: {e}")
            raise

    def _format_context(self, docs: List[Document]) -> str:
        """Format retrieved documents into context string"""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"Document {i} (Source: {source}):\n{content}")
        return "\n\n".join(context_parts)

    def generate_response(self, question: str, docs: List[Document]) -> Optional[Dict[str, Any]]:
        """
        Generate a response using retrieved documents

        Args:
            question: User question
            docs: Retrieved documents

        Returns:
            Dict with 'answer' and 'confidence' keys, or None if failed
        """
        try:
            if not self.chain:
                logger.error("Response generator not initialized")
                return None

            if not docs:
                return {"answer": "No relevant information found in the knowledge base.", "confidence": 0.0}

            # Format context from documents
            context = self._format_context(docs)

            # Generate response
            answer = self.chain.invoke({"context": context, "question": question})

            # Calculate confidence based on context relevance and answer quality
            confidence = self._calculate_confidence(answer, docs)

            logger.info(f"Response generated for question: {question[:50]}... (confidence: {confidence:.2f})")
            return {"answer": answer, "confidence": confidence}

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {"answer": f"Error generating response: {str(e)}", "confidence": 0.0}

    def _calculate_confidence(self, answer: str, docs: List[Document]) -> float:
        """
        Calculate confidence score for the generated response

        Args:
            answer: Generated answer text
            docs: Retrieved documents

        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Simple confidence calculation based on:
            # 1. Number of documents retrieved
            # 2. Whether answer contains uncertainty markers
            # 3. Answer length (longer answers might indicate more comprehensive info)

            base_confidence = min(len(docs) / 5.0, 1.0)  # Max confidence at 5 docs

            # Reduce confidence if answer contains uncertainty
            uncertainty_markers = ["i don't know", "unclear", "not sure", "insufficient", "limited information"]
            if any(marker in answer.lower() for marker in uncertainty_markers):
                base_confidence *= 0.7

            # Boost confidence for longer, more detailed answers
            if len(answer) > 100:
                base_confidence *= 1.1
            elif len(answer) < 50:
                base_confidence *= 0.8

            return min(max(base_confidence, 0.0), 1.0)

        except Exception as e:
            logger.warning(f"Confidence calculation failed: {e}")
            return 0.5  # Default medium confidence