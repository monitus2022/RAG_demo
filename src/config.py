import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to manage environment variables"""

    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    # API Keys
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # Database Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/agency/agency_data.db")

    # ChromaDB Configuration
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
    WIKI_DATA_PATH = os.getenv("WIKI_DATA_PATH", "data/wiki")

    # Other Settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if cls.LLM_PROVIDER == "openrouter" and not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required when using openrouter provider")

# Validate configuration on import
Config.validate()