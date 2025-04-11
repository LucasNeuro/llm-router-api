import os
from openai import OpenAI
from loguru import logger
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Inicializa o cliente OpenAI apenas com a API key
# Remova qualquer outro parâmetro não suportado pela versão atual da biblioteca
client = OpenAI(
    api_key=os.getenv("GPT_API_KEY")
)

async def generate_response(
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
        if not client:
            raise ValueError("Cliente OpenAI não inicializado")
            
        # Log da chamada
        logger.info(f"Chamando GPT com modelo {model}")
        
        # Prepara os parâmetros
        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        
        # Adiciona max_tokens se especificado
        if max_tokens:
            params["max_tokens"] = max_tokens
            
        # Filtra kwargs para incluir apenas parâmetros suportados
        # Isso evita passar parâmetros como 'proxies' que podem não ser suportados
        supported_params = ["frequency_penalty", "presence_penalty", "stop", "timeout"]
        for key in kwargs:
            if key in supported_params:
                params[key] = kwargs[key]
            
        # Faz a chamada à API
        response = await client.chat.completions.create(**params)
        
        # Processa a resposta
        if stream:
            return response
        else:
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"Erro ao gerar resposta com GPT: {str(e)}")
        raise