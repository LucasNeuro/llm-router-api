import os
import sys
from pathlib import Path
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from dotenv import load_dotenv
import requests

def print_step(message: str, success: bool = None):
    """Imprime uma mensagem de status com emoji"""
    if success is True:
        print(f"✅ {message}")
    elif success is False:
        print(f"❌ {message}")
    else:
        print(f"ℹ️ {message}")

def verify_api_key(api_key: str) -> bool:
    """Verifica se a chave API é válida fazendo uma chamada simples"""
    try:
        response = requests.get(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao verificar chave API: {str(e)}")
        return False

def main():
    print("\n=== Teste da Chave API do Mistral ===\n")
    
    # 1. Procura o arquivo .env
    env_path = Path(__file__).parent.parent.parent / '.env'
    print_step(f"Procurando arquivo .env em: {env_path}")
    
    if not env_path.exists():
        print_step("Arquivo .env não encontrado", False)
        return
    
    print_step("Arquivo .env encontrado", True)
    
    # 2. Carrega as variáveis de ambiente
    load_dotenv(env_path)
    
    # 3. Verifica a chave API
    api_key = os.getenv('MISTRAL_API_KEY')
    if not api_key:
        print_step("MISTRAL_API_KEY não encontrada no arquivo .env", False)
        return
    
    print_step(f"MISTRAL_API_KEY encontrada: {api_key[:10]}...", True)
    
    # 4. Verifica se a chave é válida
    print_step("\nVerificando validade da chave API...")
    if not verify_api_key(api_key):
        print_step("❌ Chave API inválida ou não autorizada", False)
        print("\nSugestões:")
        print("1. Verifique se a chave está correta no arquivo .env")
        print("2. Obtenha uma nova chave API em: https://mistral.ai/")
        print("3. Certifique-se que sua conta está ativa e tem créditos disponíveis")
        return
    
    print_step("Chave API válida", True)
    
    try:
        # 5. Configura o cliente Mistral
        client = MistralClient(api_key=api_key)
        print_step("Configuração do Mistral realizada", True)
        
        # 6. Testa a chamada ao modelo
        print_step("\nTestando chamada ao modelo...")
        
        messages = [
            ChatMessage(role="user", content="Qual é a capital do Brasil?")
        ]
        
        response = client.chat(
            model="mistral-tiny",
            messages=messages
        )
        
        if response and response.choices:
            print_step("\n✅ Teste bem sucedido!", True)
            print("\nResposta do modelo:")
            print("-" * 50)
            print(response.choices[0].message.content)
            print("-" * 50)
        else:
            print_step("Resposta vazia do modelo", False)
            
    except Exception as e:
        print_step(f"Erro: {str(e)}", False)
        if hasattr(e, 'response'):
            print(f"Resposta: {e.response.text}")
        print("\nSugestões:")
        print("1. Verifique se a chave está correta no arquivo .env")
        print("2. Obtenha uma nova chave API em: https://mistral.ai/")
        print("3. Certifique-se que sua conta está ativa e tem créditos disponíveis")

if __name__ == "__main__":
    main() 