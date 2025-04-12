import os
from typing import Dict, Any, Optional
import httpx
import json
from api.utils.logger import logger

# Configurações do Claude
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
if not CLAUDE_API_KEY:
    logger.warning("CLAUDE_API_KEY não encontrada nas variáveis de ambiente")

# Modelo padrão do Claude
CLAUDE_MODEL = "claude-3-opus-20240229"  # Modelo mais avançado
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

async def call_claude(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Chama o modelo Claude da Anthropic
    """
    try:
        if not CLAUDE_API_KEY:
            raise ValueError("CLAUDE_API_KEY não configurada")
            
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # Prepara o corpo da requisição
        data = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Adiciona system prompt se existir
        if system_prompt:
            data["system"] = system_prompt
            
        # Realiza a chamada para a API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                CLAUDE_URL,
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                logger.error(f"Erro na API do Claude: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                raise ValueError(f"Erro na API do Claude: {response.status_code} - {response.text}")
                
            response_data = response.json()
            
            # Extrai o texto da resposta
            content = response_data.get("content", [])
            text = ""
            for item in content:
                if item.get("type") == "text":
                    text += item.get("text", "")
            
            if not text:
                raise ValueError("Resposta vazia do Claude")
                
            return {
                "text": text,
                "model": "claude",
                "success": True,
                "confidence": 1.0,
                "usage": response_data.get("usage", {})
            }
            
    except Exception as e:
        error_msg = f"Erro ao chamar Claude: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "claude",
            "success": False,
            "confidence": 0.0
        } 