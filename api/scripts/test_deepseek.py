import os
from dotenv import load_dotenv
import requests
import json
from pathlib import Path
import sys

def test_deepseek_key():
    """
    Script para testar a chave API do DeepSeek
    """
    print("\n=== Teste da Chave API do DeepSeek ===\n")
    
    # Carrega o arquivo .env
    env_path = Path(__file__).parent.parent.parent / '.env'
    print(f"Procurando arquivo .env em: {env_path}")
    
    if not env_path.exists():
        print("❌ Erro: Arquivo .env não encontrado!")
        return False
    
    print("✅ Arquivo .env encontrado")
    load_dotenv(dotenv_path=env_path)
    
    # Obtém a chave API
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ Erro: DEEPSEEK_API_KEY não encontrada no arquivo .env")
        return False
    
    print(f"✅ DEEPSEEK_API_KEY encontrada: {api_key[:10]}...")
    
    try:
        # Configuração da API do DeepSeek
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Dados para o teste
        data = {
            "messages": [
                {"role": "user", "content": "Qual é a capital do Brasil?"}
            ],
            "model": "deepseek-chat",
            "temperature": 0.7
        }
        
        # URL da API
        url = "https://api.deepseek.com/v1/chat/completions"
        
        print("✅ Configuração do DeepSeek realizada")
        print("\nTestando chamada ao modelo...")
        
        # Faz a chamada
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                print("\n✅ Teste bem sucedido!")
                print("\nResposta do modelo:")
                print("-" * 50)
                print(result['choices'][0]['message']['content'])
                print("-" * 50)
                return True
            else:
                print("❌ Erro: Resposta vazia do modelo")
                return False
        else:
            print(f"❌ Erro: Status code {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro ao testar a chave: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_deepseek_key()
    sys.exit(0 if success else 1) 