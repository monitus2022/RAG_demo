from ollama import ChatResponse, generate
from typing import Optional

import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain import hub
from typing import List, TypedDict


class OllamaLLM:
    def __init__(self, model_name):
        self.model_name = model_name
        self.admin_prompt = {"role": "system", "content": ""}
        self.user_prompt = {"role": "user", "content": ""}

    def invoke(
        self,
        messages: Optional[dict] = None,
    ):
        if messages is None:
            messages = []
        response: ChatResponse = generate(model=self.model_name, prompt=str(messages))
        return response.response


# ollama_llm = OllamaLLM(model_name="gemma3")
# response = ollama_llm.invoke(
#     messages={
#         "question": "What is Task Decomposition??",
#         "context": """
#         This benchmark evaluates the agent’s tool use capabilities at three levels:\n\nLevel-1 evaluates the ability to call the API. Given an API’s description, the model needs to determine whether to call a given API, call it correctly, and respond properly to API returns.\nLevel-2 examines the ability to retrieve the API. The model needs to search for possible APIs that may solve the user’s requirement and learn how to use them by reading documentation.\nLevel-3 assesses the ability to plan API beyond retrieve and call. Given unclear user requests (e.g. schedule group meetings, book flight/hotel/restaurant for a trip), the model may have to conduct multiple API calls to solve it.'), Document(id='99bd0cf9-a4d1-4376-88c6-561cd242af5f', metadata={'source': 'https://lilianweng.github.io/posts/2023-06-23-agent/'}, page_content='This benchmark evaluates the agent’s tool use capabilities at three levels:\n\nLevel-1 evaluates the ability to call the API. Given an API’s description, the model needs to determine whether to call a given API, call it correctly, and respond properly to API returns.\nLevel-2 examines the ability to retrieve the API. The model needs to search for possible APIs that may solve the user’s requirement and learn how to use them by reading documentation.\nLevel-3 assesses the ability to plan API beyond retrieve and call. Given unclear user requests (e.g. schedule group meetings, book flight/hotel/restaurant for a trip), the model may have to conduct multiple API calls to solve it.'), Document(id='55092fc5-813e-408d-a994-1e0015276614', metadata={'source': 'https://lilianweng.github.io/posts/2023-06-23-agent/'}, page_content='This benchmark evaluates the agent’s tool use capabilities at three levels:\n\nLevel-1 evaluates the ability to call the API. Given an API’s description, the model needs to determine whether to call a given API, call it correctly, and respond properly to API returns.\nLevel-2 examines the ability to retrieve the API. The model needs to search for possible APIs that may solve the user’s requirement and learn how to use them by reading documentation.\nLevel-3 assesses the ability to plan API beyond retrieve and call. Given unclear user requests (e.g. schedule group meetings, book flight/hotel/restaurant for a trip), the model may have to conduct multiple API calls to solve it.'), Document(id='8b327bab-98a8-4e6c-8fbc-7f9826c16967', metadata={'source': 'https://lilianweng.github.io/posts/2023-06-23-agent/'}, page_content='This benchmark evaluates the agent’s tool use capabilities at three levels:\n\nLevel-1 evaluates the ability to call the API. Given an API’s description, the model needs to determine whether to call a given API, call it correctly, and respond properly to API returns.\nLevel-2 examines the ability to retrieve the API. The model needs to search for possible APIs that may solve the user’s requirement and learn how to use them by reading documentation.\nLevel-3 assesses the ability to plan API beyond retrieve and call. Given unclear user requests (e.g. schedule group meetings, book flight/hotel/restaurant for a trip), the model may have to conduct multiple API calls to solve it.
#         """,
#     }
# )
# print(response)


llm = OllamaLLM(model_name="llama3")

# Create vector db from chroma
embeddings = OllamaEmbeddings(model="llama3")
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  # Where to save data locally, remove if not necessary
)

loader = WebBaseLoader(
    web_paths=(["https://lilianweng.github.io/posts/2023-06-23-agent/"]),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)

vector_store.add_documents(documents=all_splits)
print("Successfully stored documents into vector DB")

prompt = hub.pull("rlm/rag-prompt"
                  , api_url="https://api.smith.langchain.com"
                  )


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str


def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(query=state["question"])
    print(f"Retrieved {len(retrieved_docs)} documents")
    return {"context": retrieved_docs}


def generate_result(state: State):
    docs_content = "\n".join([doc.page_content for doc in state["context"]])
    # Add generation logic here
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response}


graph_builder = StateGraph(State).add_sequence([retrieve, generate_result])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()

response = graph.invoke(
    {"question": "What is Task Decomposition?"}
)

print(response)
for i, j in response.items():
    print(f"{i} ---------- {j}")
