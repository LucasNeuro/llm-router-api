import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging
from datetime import datetime

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
    title="LLM Router API",
    description="API para roteamento inteligente de prompts para diferentes modelos de linguagem",
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
from api.routers import chat, health, whatsapp

# Routers com prefixo api/v1
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Router do WhatsApp sem prefixo para compatibilidade com MegaAPI
app.include_router(whatsapp.router, tags=["whatsapp"])

@app.get("/")
async def root():
    return {"message": "LLM Router API está funcionando!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)