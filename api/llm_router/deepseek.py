import os
import httpx
from typing import Dict, Any, Optional
from api.utils.logger import logger
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

# Configurações do DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # Modelo atualizado
DEEPSEEK_TIMEOUT = 90.0
DEEPSEEK_MAX_RETRIES = 3

async def call_deepseek(
    prompt: str,
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Faz uma chamada para a API do DeepSeek
    """
    try:
        if not DEEPSEEK_API_KEY:
            return {
                "text": "Erro: DEEPSEEK_API_KEY não configurada",
                "model": "deepseek",
                "success": False
            }

        # Headers da requisição
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        # Prepara os messages
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        messages.append({
            "role": "user",
            "content": prompt
        })

        # Dados da requisição
        data = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        logger.info(f"Fazendo chamada ao DeepSeek: {prompt[:50]}...")

        # Faz a chamada à API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DEEPSEEK_API_BASE}/chat/completions",
                headers=headers,
                json=data,
                timeout=DEEPSEEK_TIMEOUT
            )

            if response.status_code != 200:
                error_msg = f"Erro na API DeepSeek: Status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', {}).get('message', '')}"
                except:
                    error_msg += f" - {response.text}"

                logger.error(error_msg)
                return {
                    "text": error_msg,
                    "model": "deepseek",
                    "success": False
                }

            result = response.json()
            response_text = result["choices"][0]["message"]["content"]

            return {
                "text": response_text,
                "model": "deepseek",
                "success": True
            }

    except Exception as e:
        error_msg = f"Erro ao chamar DeepSeek: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "deepseek",
            "success": False
        }