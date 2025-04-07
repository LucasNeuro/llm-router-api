import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Configuração
BASE_URL = "http://localhost:8000"
TEST_PHONE = "5511999887766"

async def send_message(prompt: str) -> Dict[str, Any]:
    """Envia uma mensagem para a API e retorna a resposta"""
    url = f"{BASE_URL}/api/v1/chat"
    payload = {
        "prompt": prompt,
        "sender_phone": TEST_PHONE
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()

async def run_conversation_test():
    """Executa um teste de conversa com contexto"""
    print("\n=== Iniciando Teste de Conversa com Contexto ===\n")
    
    # Teste 1: Apresentação
    print("Teste 1: Apresentação")
    response = await send_message("Oi! Meu nome é João e sou programador.")
    print(f"Bot: {response['text']}\n")
    time.sleep(2)  # Pequena pausa para simular conversa natural
    
    # Teste 2: Verificar memória do nome
    print("Teste 2: Verificar memória do nome")
    response = await send_message("Qual é o meu nome mesmo?")
    print(f"Bot: {response['text']}\n")
    time.sleep(2)
    
    # Teste 3: Introduzir um tópico técnico
    print("Teste 3: Introduzir tópico técnico")
    response = await send_message("Me explique o que é Python de forma simples.")
    print(f"Bot: {response['text']}\n")
    time.sleep(2)
    
    # Teste 4: Referência ao contexto anterior
    print("Teste 4: Referência ao contexto anterior")
    response = await send_message("Baseado no que você me explicou sobre Python, ele seria bom para análise de dados?")
    print(f"Bot: {response['text']}\n")
    time.sleep(2)
    
    # Teste 5: Verificar memória de longo prazo
    print("Teste 5: Memória de longo prazo")
    print("Aguardando 10 segundos para simular passagem de tempo...")
    time.sleep(10)
    response = await send_message("Você ainda lembra sobre o que estávamos conversando sobre programação?")
    print(f"Bot: {response['text']}\n")
    
    # Teste 6: Mudança de contexto
    print("Teste 6: Mudança de contexto")
    response = await send_message("Agora me fale sobre inteligência artificial.")
    print(f"Bot: {response['text']}\n")
    time.sleep(2)
    
    # Teste 7: Referência cruzada
    print("Teste 7: Referência cruzada")
    response = await send_message("Como Python e IA se relacionam, considerando nossa conversa anterior?")
    print(f"Bot: {response['text']}\n")
    
    print("\n=== Teste de Conversa Finalizado ===")

if __name__ == "__main__":
    print("Iniciando testes de conversa...")
    asyncio.run(run_conversation_test()) 