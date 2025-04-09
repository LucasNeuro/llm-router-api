from loguru import logger
import sys
import json
from datetime import datetime

# Remove handlers padrão
logger.remove()

# Adiciona apenas handler para console
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

def log_api_request(request_data: dict, route: str):
    """Log formatado para requisições API"""
    logger.info(f"API Request to {route}")

def log_api_response(response_data: dict, route: str, success: bool = True):
    """Log formatado para respostas API"""
    status = "Success" if success else "Error"
    logger.info(f"API Response from {route} - Status: {status}")

def log_llm_call(model: str, prompt: str):
    """Log formatado para chamadas LLM"""
    logger.info(f"LLM Call to {model}")

def log_llm_response(model: str, response: str, success: bool = True):
    """Log formatado para respostas LLM"""
    status = "Success" if success else "Error"
    logger.info(f"LLM Response from {model} - Status: {status}")

def log_error(error: Exception, context: str = None):
    """Log formatado para erros"""
    logger.error(f"Error {f'in {context} ' if context else ''}- {str(error)}")

def log_memory_operation(operation: str, phone: str, details: dict = None):
    """Log formatado para operações de memória"""
    log_msg = f"Memory {operation} for {phone}"
    if details:
        log_msg += f" - Details: {json.dumps(details, ensure_ascii=False)}"
    logger.info(log_msg)

def log_memory_stats(phone: str, total_messages: int, active: bool):
    """Log formatado para estatísticas de memória"""
    status = "active" if active else "inactive"
    logger.info(f"Memory stats for {phone}: {total_messages} messages, status: {status}")

# Exemplo de uso:
if __name__ == "__main__":
    logger.info("Teste de log info")
    logger.warning("Teste de log warning")
    logger.error("Teste de log error") 