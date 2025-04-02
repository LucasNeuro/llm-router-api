import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Agora podemos importar os módulos da api
import uvicorn
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

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
        log_level="error"  # Mudando para mostrar apenas erros
    )
    
    # Inicia o servidor
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    start_server() 