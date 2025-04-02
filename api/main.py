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
from api.routers import chat, whatsapp
import logging
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
log_path = Path("api/logs")
log_path.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"api/logs/api_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Cria a aplicação FastAPI
app = FastAPI(
    title="LLM Router API",
    description="API para roteamento inteligente de requisições para diferentes modelos de LLM",
    version="1.0.0"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(whatsapp.router, prefix="/api/v1", tags=["whatsapp"])

@app.get("/")
async def root():
    return {"message": "LLM Router API está funcionando!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)