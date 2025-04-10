import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging
from datetime import datetime
from api.routers import chat, health, whatsapp, agent_whatsapp
from api.utils.logger import logger
from api.utils.cache_manager import cache_manager

# Carrega variáveis de ambiente
load_dotenv()

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Cria a aplicação FastAPI
app = FastAPI(
    title="MPC API",
    description="API para roteamento inteligente de LLMs",
    version="1.0.0"
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Router do WhatsApp sem prefixo para compatibilidade com MegaAPI
app.include_router(whatsapp.router, prefix="/api/v1", tags=["whatsapp"])

# Router dos agentes
app.include_router(agent_whatsapp.router, prefix="/api/v1", tags=["agents"])

@app.on_event("startup")
async def startup_event():
    """Evento de inicialização da API"""
    try:
        # Inicializa tabela de cache
        cache_manager._ensure_cache_table()
        logger.info("API iniciada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar API: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de encerramento da API"""
    try:
        logger.info("API encerrada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao encerrar API: {str(e)}")

@app.get("/")
async def root():
    """Rota raiz"""
    return {
        "message": "MPC API - Roteamento Inteligente de LLMs",
        "version": "1.0.0"
    }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requisições"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Erro na requisição: {str(e)}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)