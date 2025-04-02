import os
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
import sys

def test_gemini_key():
    """
    Script para testar a chave API do Gemini
    """
    print("\n=== Teste da Chave API do Gemini ===\n")
    
    # Carrega o arquivo .env
    env_path = Path(__file__).parent.parent.parent / '.env'
    print(f"Procurando arquivo .env em: {env_path}")
    
    if not env_path.exists():
        print("❌ Erro: Arquivo .env não encontrado!")
        return False
    
    print("✅ Arquivo .env encontrado")
    load_dotenv(dotenv_path=env_path)
    
    # Obtém a chave API
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Erro: GEMINI_API_KEY não encontrada no arquivo .env")
        return False
    
    print(f"✅ GEMINI_API_KEY encontrada: {api_key[:10]}...")
    
    try:
        # Configura o Gemini
        genai.configure(api_key=api_key)
        print("✅ Configuração do Gemini realizada")
        
        # Lista os modelos disponíveis
        print("\nModelos disponíveis:")
        models = list(genai.list_models())
        for model in models:
            print(f"- {model.name}")
        
        # Seleciona o modelo mais apropriado
        model_name = "models/gemini-1.5-pro"  # Usando a versão mais recente disponível
        print(f"\nUsando modelo: {model_name}")
        
        # Tenta criar o modelo
        model = genai.GenerativeModel(model_name)
        print("✅ Modelo criado com sucesso")
        
        # Configura a geração
        generation_config = {
            "temperature": 0.7,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }
        
        # Tenta fazer uma chamada simples
        print("\nTestando chamada ao modelo...")
        response = model.generate_content(
            "Olá, pode me dizer qual é a capital do Brasil?",
            generation_config=generation_config
        )
        
        if response and response.text:
            print("\n✅ Teste bem sucedido!")
            print("\nResposta do modelo:")
            print("-" * 50)
            print(response.text)
            print("-" * 50)
            return True
        else:
            print("❌ Erro: Resposta vazia do modelo")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro ao testar a chave: {str(e)}")
        print("\nDicas de solução:")
        print("1. Verifique se a chave API está correta")
        print("2. Certifique-se de que sua conta tem acesso ao Gemini Pro")
        print("3. Tente gerar uma nova chave API em: https://makersuite.google.com/app/apikey")
        return False

if __name__ == "__main__":
    success = test_gemini_key()
    sys.exit(0 if success else 1)