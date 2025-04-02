import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Agora podemos importar os módulos da api
import uvicorn
from dotenv import load_dotenv
from loguru import logger

# Carrega variáveis de ambiente
load_dotenv()

# Configura o logger apenas para console
logger.remove()  # Remove todos os handlers
logger.add(sys.stderr, level="INFO")  # Adiciona apenas log no console

def start_server():
    """Inicia o servidor FastAPI"""
    # Configurações do servidor
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))  # Mudado para PORT para compatibilidade com Render
    
    # Configuração do uvicorn
    config = uvicorn.Config(
        "api.main:app",
        host=host,
        port=port,
        reload=False,  # Desabilitado reload em produção
        log_level="info",
        access_log=True
    )
    
    # Inicia o servidor
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    start_server() 