import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from api.utils.logger import logger

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY não encontrada nas variáveis de ambiente")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Lista os modelos disponíveis para debug
        try:
            models = genai.list_models()
            logger.info("Modelos Gemini disponíveis:")
            for model in models:
                logger.info(f"- {model.name}")
        except Exception as e:
            logger.warning(f"Não foi possível listar modelos Gemini: {str(e)}")

    except Exception as e:
        logger.error(f"Erro ao configurar Gemini: {str(e)}")

# Nome correto do modelo Gemini (baseado na lista disponível)
GEMINI_MODEL = 'gemini-1.5-flash-latest'  # Modelo disponível e rápido

async def call_gemini(prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Call Gemini model with the given prompt
    """
    try:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não configurada")

        # Combine system prompt and user prompt if system prompt exists
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        try:
            # Configurar o modelo
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            # Criar o chat e gerar resposta
            chat = model.start_chat(history=[])
            response = chat.send_message(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            if not response.text:
                raise ValueError("Resposta vazia do modelo Gemini")
                
            return {
                "text": response.text,
                "model": "gemini",
                "success": True,
                "confidence": 1.0
            }
            
        except Exception as e:
            if "not found" in str(e) or "not supported" in str(e):
                logger.error(f"Modelo {GEMINI_MODEL} não disponível. Erro: {str(e)}")
                # Tenta listar modelos disponíveis
                try:
                    models = genai.list_models()
                    logger.info("Modelos disponíveis:")
                    for model in models:
                        logger.info(f"- {model.name}")
                except Exception as list_e:
                    logger.error(f"Não foi possível listar modelos: {str(list_e)}")
            elif "API_KEY_INVALID" in str(e):
                logger.error("API key do Gemini inválida")
                raise ValueError("API key do Gemini inválida")
            raise e
            
    except Exception as e:
        error_msg = f"Erro ao chamar Gemini: {str(e)}"
        logger.error(error_msg)
        return {
            "text": error_msg,
            "model": "gemini",
            "success": False,
            "confidence": 0.0
        }