from typing import Dict, Any
import tiktoken
from api.utils.logger import logger

# Configurações de preços e limites dos modelos
MODEL_PRICING = {
    "gpt": {
        "model": "gpt-4",  # GPT-4 turbo
        "input_price_per_1k": 0.01,  # $0.01 por 1k tokens de input
        "output_price_per_1k": 0.03,  # $0.03 por 1k tokens de output
        "doc_url": "https://openai.com/pricing"
    },
    "deepseek": {
        "model": "deepseek-chat",
        "input_price_per_1k": 0.002,  # $0.002 por 1k tokens de input
        "output_price_per_1k": 0.002,  # $0.002 por 1k tokens de output
        "doc_url": "https://api-docs.deepseek.com/quick_start/pricing/"
    },
    "mistral": {
        "model": "mistral-medium",
        "input_price_per_1k": 0.002,  # $0.002 por 1k tokens de input
        "output_price_per_1k": 0.002,  # $0.002 por 1k tokens de output
        "doc_url": "https://docs.mistral.ai/platform/pricing"
    },
    "gemini": {
        "model": "gemini-pro",
        "input_price_per_1k": 0.001,  # $0.001 por 1k tokens de input
        "output_price_per_1k": 0.001,  # $0.001 por 1k tokens de output
        "doc_url": "https://ai.google.dev/pricing"
    }
}

def format_usd(value: float) -> str:
    """
    Formata um valor em dólares
    """
    return f"${value:.6f}"

def count_tokens(text: str) -> int:
    """
    Conta tokens usando o tokenizador do GPT (aproximação para outros modelos)
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Erro ao contar tokens: {str(e)}")
        return len(text.split()) * 2  # Estimativa aproximada se falhar

def get_model_info(model: str) -> dict:
    """
    Retorna informações de preço e documentação para cada modelo
    """
    models = {
        "gpt": {
            "name": "gpt-4-turbo-preview",
            "input_price": 0.01,  # $0.01 por 1k tokens
            "output_price": 0.03,  # $0.03 por 1k tokens
            "doc_url": "https://openai.com/chatgpt/pricing/"
        },
        "gemini": {
            "name": "gemini-pro",
            "input_price": 0.00025,  # $0.00025 por 1k tokens (texto)
            "output_price": 0.0005,  # $0.0005 por 1k tokens
            "doc_url": "https://ai.google.dev/gemini-api/docs/pricing"
        },
        "mistral": {
            "name": "mistral-large-latest",
            "input_price": 0.008,  # $0.008 por 1k tokens
            "output_price": 0.024,  # $0.024 por 1k tokens
            "doc_url": "https://mistral.ai/products/la-plateforme#pricing"
        },
        "deepseek": {
            "name": "deepseek-chat",
            "input_price": 0.002,  # $0.002 por 1k tokens
            "output_price": 0.006,  # $0.006 por 1k tokens
            "doc_url": "https://api-docs.deepseek.com/quick_start/pricing/"
        }
    }
    
    return models.get(model, models["gpt"])

def analyze_cost(model: str, prompt: str, response: str) -> Dict[str, Any]:
    """Analisa o custo da chamada ao modelo."""
    try:
        # Taxa de câmbio USD para BRL (atualizar conforme necessário)
        USD_TO_BRL = 5.0

        # Calcula tokens
        prompt_tokens = count_tokens(prompt)
        completion_tokens = count_tokens(response)
        total_tokens = prompt_tokens + completion_tokens

        # Obtém informações do modelo
        model_info = get_model_info(model)
        
        # Calcula custos em USD
        prompt_cost = (prompt_tokens / 1000) * model_info["input_price"]
        completion_cost = (completion_tokens / 1000) * model_info["output_price"]
        total_cost = prompt_cost + completion_cost

        # Calcula custos em diferentes formatos
        total_cost_brl = total_cost * USD_TO_BRL
        total_cost_cents_brl = int(total_cost_brl * 100)  # Centavos como inteiro
        total_cost_cents_usd = int(total_cost * 100)      # Centavos USD como inteiro

        return {
            "model": model,
            "model_info": {
                "name": model_info["name"],
                "input_price": model_info["input_price"],
                "output_price": model_info["output_price"],
                "doc_url": model_info["doc_url"]
            },
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens
            },
            "costs": {
                "usd": {
                    "cents": total_cost_cents_usd,
                    "dollars": int(total_cost),
                    "formatted": f"${total_cost:.6f}"
                },
                "brl": {
                    "cents": total_cost_cents_brl,
                    "dollars": int(total_cost_brl),
                    "formatted": f"R${total_cost_brl:.2f}"
                }
            },
            "pricing": {
                "input_price_per_1k": model_info["input_price"],
                "output_price_per_1k": model_info["output_price"]
            }
        }
    except Exception as e:
        logger.error(f"Erro ao analisar custo: {str(e)}")
        return {
            "model": model,
            "model_info": {
                "name": "unknown",
                "input_price": 0,
                "output_price": 0,
                "doc_url": ""
            },
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0
            },
            "costs": {
                "usd": {
                    "cents": 0,
                    "dollars": 0,
                    "formatted": "$0.00"
                },
                "brl": {
                    "cents": 0,
                    "dollars": 0,
                    "formatted": "R$0.00"
                }
            },
            "pricing": {
                "input_price_per_1k": 0,
                "output_price_per_1k": 0
            }
        }