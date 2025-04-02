import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Pega a chave da API
api_key = os.getenv("GPT_API_KEY")
print("\n🔑 Verificando chave da API:")
print(f"- Chave encontrada: {'Sim' if api_key else 'Não'}")
print(f"- Comprimento: {len(api_key) if api_key else 0} caracteres")

# Configura o cliente OpenAI
client = AsyncOpenAI(api_key=api_key)

async def test_gpt():
    """
    Testa a conexão com a API do GPT
    """
    try:
        print("\n🔄 Testando conexão com GPT API...")
        
        # Tenta fazer uma chamada simples
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Você é um assistente prestativo."},
                {"role": "user", "content": "Olá, quem  e o  primeiro  presidente  do  dos  estados  unidos ?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        # Verifica se a resposta foi bem sucedida
        if response and response.choices[0].message.content:
            print("✅ Conexão com GPT API estabelecida com sucesso!")
            print(f"\nResposta de teste:\n{response.choices[0].message.content}")
            print(f"\nModelo usado: {response.model}")
            print(f"Tokens utilizados: {response.usage.total_tokens}")
            return True
            
    except Exception as e:
        print("❌ Erro ao testar GPT API:")
        print(f"Detalhes do erro: {str(e)}")
        return False

if __name__ == "__main__":
    # Verifica se a chave API está configurada
    if not os.getenv("GPT_API_KEY"):
        print("❌ GPT_API_KEY não encontrada nas variáveis de ambiente!")
        exit(1)
        
    # Executa o teste
    asyncio.run(test_gpt()) 