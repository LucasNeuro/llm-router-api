import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

def check_imports():
    """Verifica se todos os módulos necessários podem ser importados corretamente"""
    print("\n=== VERIFICAÇÃO DE IMPORTAÇÕES ===")
    
    try:
        print("✅ Importando módulos principais... ", end="")
        from fastapi import FastAPI
        import httpx
        from pydantic import BaseModel
        print("OK")
    except ImportError as e:
        print(f"FALHA: {str(e)}")
        
    try:
        print("✅ Importando modelos de agente... ", end="")
        from models.agent import Agent, g4_agent
        print(f"OK - Agente {g4_agent.config.name} carregado!")
    except ImportError as e:
        print(f"FALHA: {str(e)}")
        
    try:
        print("✅ Importando serviço de agente... ", end="")
        from utils.agent_service import AgentService, agent_service
        print(f"OK - {len(agent_service.agents)} agentes registrados")
    except ImportError as e:
        print(f"FALHA: {str(e)}")
        
    try:
        print("✅ Importando router de agente... ", end="")
        from routers.agent_whatsapp import router as agent_router
        print(f"OK - Endpoints disponíveis")
    except ImportError as e:
        print(f"FALHA: {str(e)}")
        
    try:
        print("✅ Importando main... ", end="")
        from main import app
        print(f"OK - FastAPI inicializada")
    except ImportError as e:
        print(f"FALHA: {str(e)}")

def check_endpoints():
    """Verifica os endpoints disponíveis"""
    print("\n=== VERIFICAÇÃO DE ENDPOINTS ===")
    
    try:
        from main import app
        routes = [
            {"path": route.path, "name": route.name, "methods": route.methods}
            for route in app.routes
        ]
        
        # Filtra apenas rotas relacionadas a agentes
        agent_routes = [r for r in routes if "agent" in r["path"].lower()]
        
        print(f"Total de endpoints: {len(routes)}")
        print(f"Endpoints de agentes: {len(agent_routes)}")
        
        print("\nEndpoints de agentes disponíveis:")
        for route in agent_routes:
            methods = ", ".join(route["methods"])
            print(f"  - {methods} {route['path']} -> {route['name']}")
            
    except Exception as e:
        print(f"FALHA: {str(e)}")

def main():
    """Função principal"""
    print("\n==== VERIFICAÇÃO DO SISTEMA DE AGENTES ====")
    
    # Verifica se os módulos podem ser importados
    check_imports()
    
    # Verifica os endpoints
    check_endpoints()
    
    print("\n==== VERIFICAÇÃO CONCLUÍDA ====")

if __name__ == "__main__":
    main() 