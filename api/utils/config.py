import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações de API
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Configurações de banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./llm_router.db")

# Configurações de cache
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hora em segundos
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))  # Máximo de itens no cache

# Configurações de fila
QUEUE_ENABLED = os.getenv("QUEUE_ENABLED", "true").lower() == "true"
QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", "100"))

# Configurações de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configurações de timeout
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # segundos

# Configurações de rate limiting
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # Requisições por minuto
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # Período em segundos

# Configurações de modelos
MODEL_CONFIGS = {
    "gpt": {
        "name": "gpt-4",
        "input_price": 0.03,  # USD por 1K tokens
        "output_price": 0.06,  # USD por 1K tokens
        "doc_url": "https://openai.com/pricing",
    },
    "deepseek": {
        "name": "deepseek-chat",
        "input_price": 0.02,  # USD por 1K tokens
        "output_price": 0.04,  # USD por 1K tokens
        "doc_url": "https://deepseek.com/pricing",
    },
    "gemini": {
        "name": "gemini-pro",
        "input_price": 0.00025,  # USD por 1K tokens
        "output_price": 0.0005,  # USD por 1K tokens
        "doc_url": "https://ai.google.dev/gemini-api/docs/pricing",
    },
    "mistral": {
        "name": "mistral-medium",
        "input_price": 0.002,  # USD por 1K tokens
        "output_price": 0.006,  # USD por 1K tokens
        "doc_url": "https://mistral.ai/pricing",
    },
}

# Taxa de conversão USD para BRL
USD_TO_BRL = float(os.getenv("USD_TO_BRL", "5.0"))
