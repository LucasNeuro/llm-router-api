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

# Configuração de logging
log_path = Path("api/logs")
log_path.mkdir(exist_ok=True)
logger.add(
    log_path / "api.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO"
)

def start_server():
    """Inicia o servidor FastAPI"""
    # Configurações do servidor
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Configuração do uvicorn
    config = uvicorn.Config(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
    
    logger.info(f"Iniciando servidor na porta {port}...")
    
    # Inicia o servidor
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {str(e)}")
        raise 