import os
from openai import OpenAI
from loguru import logger
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração do cliente OpenAI
def get_openai_client() -> OpenAI:
    """Cria e configura o cliente OpenAI com retry e timeout"""
    try:
        # Configuração do proxy se existir
        proxy = os.getenv("OPENAI_PROXY")
        
        # Cria o cliente com configurações básicas
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=httpx.Timeout(30.0, connect=10.0),
            max_retries=3
        )
        
        # Configura o proxy se existir
        if proxy:
            client.http_client.set_proxy(proxy)
            
        return client
    except Exception as e:
        logger.error(f"Erro ao criar cliente OpenAI: {str(e)}")
        raise

# Inicializa o cliente
client = get_openai_client()

def generate_response(
    prompt: str,
    model: str = "gpt-4-turbo-preview",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stream: bool = False,
    **kwargs: Dict[str, Any]
) -> str:
    """
    Gera uma resposta usando o modelo GPT especificado.
    
    Args:
        prompt: O texto do prompt
        model: O modelo a ser usado (default: gpt-4-turbo-preview)
        temperature: Temperatura para controle de criatividade (0.0 a 1.0)
        max_tokens: Número máximo de tokens na resposta
        stream: Se True, retorna a resposta em streaming
        **kwargs: Argumentos adicionais para a API
        
    Returns:
        str: A resposta gerada pelo modelo
    """
    try:
        # Log da chamada
        logger.info(f"Chamando GPT com modelo {model}")
        
        # Prepara os parâmetros
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            **kwargs
        }
        
        # Adiciona max_tokens se especificado
        if max_tokens:
            params["max_tokens"] = max_tokens
            
        # Faz a chamada à API
        response = client.chat.completions.create(**params)
        
        # Processa a resposta
        if stream:
            return response
        else:
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"Erro ao gerar resposta com GPT: {str(e)}")
        raise