import os
from dotenv import load_dotenv
from pathlib import Path
import sys

def test_env_variables():
    """
    Script para testar todas as variáveis de ambiente necessárias
    """
    print("\n=== Teste das Variáveis de Ambiente ===\n")
    
    # Carrega o arquivo .env
    env_path = Path(__file__).parent.parent.parent / '.env'
    print(f"Procurando arquivo .env em: {env_path}")
    
    if not env_path.exists():
        print("❌ Erro: Arquivo .env não encontrado!")
        return False
    
    print("✅ Arquivo .env encontrado")
    load_dotenv(dotenv_path=env_path)
    
    # Lista de variáveis obrigatórias
    required_vars = {
        'API_PORT': 'Porta da API',
        'API_HOST': 'Host da API',
        'GEMINI_API_KEY': 'Chave API do Gemini',
        'DEEPSEEK_API_KEY': 'Chave API do DeepSeek',
        'NEO4J_URI': 'URI do Neo4j',
        'NEO4J_USER': 'Usuário do Neo4j',
        'NEO4J_PASSWORD': 'Senha do Neo4j',
        'JWT_SECRET': 'Chave secreta para JWT',
    }
    
    all_ok = True
    print("\nVerificando variáveis de ambiente:")
    print("-" * 50)
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mostra apenas os primeiros caracteres para chaves sensíveis
            if 'KEY' in var or 'PASSWORD' in var or 'SECRET' in var:
                display_value = f"{value[:10]}..."
            else:
                display_value = value
            print(f"✅ {description} ({var}): {display_value}")
        else:
            print(f"❌ {description} ({var}): Não encontrada")
            all_ok = False
    
    print("\n=== Resultado Final ===")
    if all_ok:
        print("✅ Todas as variáveis de ambiente estão configuradas!")
    else:
        print("❌ Algumas variáveis de ambiente estão faltando!")
    
    return all_ok

if __name__ == "__main__":
    success = test_env_variables()
    sys.exit(0 if success else 1) 