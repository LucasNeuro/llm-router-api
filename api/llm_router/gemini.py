import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from api.utils.logger import logger

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY não encontrada nas variáveis de ambiente")

genai.configure(api_key=GEMINI_API_KEY)

# Nome correto do modelo Gemini
GEMINI_MODEL = 'models/gemini-1.5-pro'

async def call_gemini(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Gemini model with the given prompt
    """
    try:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não configurada")

        # Combine system prompt and user prompt if system prompt exists
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # Configurar o modelo com o nome correto
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Criar o chat e gerar resposta
        chat = model.start_chat()
        response = chat.send_message(full_prompt)
        
        if not response.text:
            raise ValueError("Resposta vazia do modelo Gemini")
            
        return {
            "text": response.text,
            "model": "gemini",
            "success": True
        }
        
    except Exception as e:
        error_msg = f"Error calling Gemini: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "gemini",
            "success": False
        }