import os
from typing import Dict, Any, Optional
import httpx
import json
from api.utils.logger import logger

# Configurações do GPT
GPT_API_KEY = os.getenv("GPT_API_KEY")
if not GPT_API_KEY:
    logger.warning("GPT_API_KEY não encontrada nas variáveis de ambiente")

# Modelo padrão do GPT
GPT_MODEL = "gpt-4"  # Modelo mais avançado
GPT_URL = "https://api.openai.com/v1/chat/completions"

async def call_gpt(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Chama o modelo GPT da OpenAI
    """
    try:
        if not GPT_API_KEY:
            raise ValueError("GPT_API_KEY não configurada")
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GPT_API_KEY}"
        }
        
        # Prepara os mensagens
        messages = []
        
        # Adiciona system prompt se existir
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Adiciona mensagem do usuário
        messages.append({"role": "user", "content": prompt})
        
        # Prepara o corpo da requisição
        data = {
            "model": GPT_MODEL,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
            
        # Realiza a chamada para a API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GPT_URL,
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Erro na API do GPT: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                raise ValueError(f"Erro na API do GPT: {response.status_code} - {response.text}")
                
            response_data = response.json()
            
            # Extrai o texto da resposta
            choices = response_data.get("choices", [])
            if not choices:
                raise ValueError("Resposta vazia do GPT")
                
            text = choices[0].get("message", {}).get("content", "")
            
            if not text:
                raise ValueError("Texto vazio na resposta do GPT")
                
            return {
                "text": text,
                "model": "gpt",
                "success": True,
                "confidence": 1.0,
                "usage": response_data.get("usage", {})
            }
            
    except Exception as e:
        error_msg = f"Erro ao chamar GPT: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "gpt",
            "success": False,
            "confidence": 0.0
        }