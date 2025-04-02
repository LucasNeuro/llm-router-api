import os
from typing import Dict, Any, Optional
from ..utils.logger import logger
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = MistralClient(api_key=MISTRAL_API_KEY)
MISTRAL_MODEL = "mistral-large-latest"

async def call_mistral(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Chama a API do Mistral usando o cliente oficial
    """
    try:
        if not MISTRAL_API_KEY:
            return {
                "text": "MISTRAL_API_KEY não configurada",
                "model": "mistral",
                "success": False
            }

        logger.info(f"Iniciando chamada ao Mistral. Prompt: {prompt[:50]}...")
        
        messages = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        # Execute in thread pool since client is not async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
        )
        
        response_text = response.choices[0].message.content
        logger.info("Resposta recebida do Mistral com sucesso")
        
        return {
            "text": response_text,
            "model": "mistral",
            "success": True,
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
            
    except Exception as e:
        error_msg = f"Erro ao chamar Mistral: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "mistral",
            "success": False
        }