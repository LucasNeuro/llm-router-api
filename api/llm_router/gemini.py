import os
import google.generativeai as genai
from typing import Dict, Any, Optional
from utils.logger import logger

# Configurações do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro-latest"  # Modelo atualizado

def configure_gemini():
    """Configura o cliente Gemini com a chave API"""
    try:
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY não configurada")
            return None
            
        # Log da chave (primeiros 8 caracteres)
        logger.info(f"Valor da GEMINI_API_KEY: {GEMINI_API_KEY[:8]}...")
        
        # Configura a chave API
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Lista modelos disponíveis
        models = [m.name for m in genai.list_models()]
        logger.info(f"Modelos disponíveis: {models}")
        
        # Cria o modelo
        model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info("Modelo Gemini criado com sucesso")
        
        # Testa o modelo
        try:
            response = model.generate_content("Teste")
            if response and response.text:
                logger.info("Teste de chamada ao Gemini bem sucedido")
                return model
            else:
                logger.error("Teste de chamada ao Gemini falhou - resposta vazia")
                return None
        except Exception as e:
            logger.error(f"Erro ao testar chamada ao Gemini: {str(e)}")
            return None
                
    except Exception as e:
        logger.error(f"Erro ao configurar Gemini: {str(e)}")
        return None

async def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Faz uma chamada para a API do Google Gemini
    """
    try:
        # Configura o Gemini e obtém o modelo
        model = configure_gemini()
        
        if not model:
            error_msg = "Não foi possível configurar o modelo Gemini. Verifique a chave API e os logs."
            logger.error(error_msg)
            return {
                "text": f"Erro: {error_msg}",
                "model": "gemini",
                "success": False
            }
        
        # Prepara o prompt completo
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # Faz a chamada
        response = model.generate_content(full_prompt)
        
        if not response or not response.text:
            error_msg = "Resposta vazia do modelo Gemini"
            logger.error(error_msg)
            return {
                "text": f"Erro: {error_msg}",
                "model": "gemini",
                "success": False
            }
        
        logger.info("Resposta recebida do Gemini com sucesso")
        
        return {
            "text": response.text,
            "model": "gemini",
            "success": True
        }
        
    except Exception as e:
        error_msg = f"Erro ao chamar Gemini: {str(e)}"
        logger.error(error_msg)
        return {
            "text": f"Erro: {error_msg}",
            "model": "gemini",
            "success": False
        }