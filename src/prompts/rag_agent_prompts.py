# RAG Agent Prompts

RAG_RESPONSE_PROMPT = """
You are a knowledgeable assistant specializing in Hong Kong housing estates.
Answer the user's question based on the provided context from wiki pages.
Be informative, accurate, and concise. If the context doesn't fully answer the question,
acknowledge the limitations and provide what information is available.

Context:
{context}

Question: {question}

Answer:"""

RAG_SUMMARY_PROMPT = """
Summarize the key information about Hong Kong housing estates from the following context.
Focus on historical, geographical, and development aspects.

Context:
{context}

Summary:"""

RAG_FOLLOWUP_PROMPT = """
Based on the context, suggest 2-3 related questions the user might ask about Hong Kong housing estates.

Context:
{context}

Suggested questions:"""