from langchain_ollama import OllamaLLM
from langchain_openai import ChatOpenAI
from config.settings import Config

# Initialize LLM connectors for different providers
def get_ollama_llm(model_name: str = None):
    """
    Initialize and return an Ollama LLM instance.
    Uses model from config if not specified.
    """
    model = model_name or Config.OLLAMA_MODEL
    return OllamaLLM(model=model)

def get_openrouter_llm(model_name: str = None):
    """
    Initialize and return an OpenRouter LLM instance via OpenAI-compatible API.
    Uses config for API key and model.
    """
    if not Config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is required when using openrouter provider")

    model = model_name or Config.OPENROUTER_MODEL
    return ChatOpenAI(
        model=model,
        openai_api_key=Config.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1"
    )

def get_llm(provider: str = None, model_name: str = None):
    """
    Factory function to get LLM based on provider from config.
    """
    provider = provider or Config.LLM_PROVIDER

    if provider == "ollama":
        return get_ollama_llm(model_name)
    elif provider == "openrouter":
        return get_openrouter_llm(model_name)
    else:
        raise ValueError(f"Unsupported provider: {provider}")