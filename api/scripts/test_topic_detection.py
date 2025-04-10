import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
script_dir = Path(__file__).parent
root_dir = script_dir.parent.parent
sys.path.append(str(root_dir))

from api.utils.conversation_memory import ConversationManager
from api.utils.logger import logger

async def test_topic_detection():
    """Testa a detecção de tópicos baseada em IA"""
    print("Testando detecção de tópicos baseada em IA...")
    
    # Cria o gerenciador de conversas
    mgr = ConversationManager()
    
    # Teste 1: Mudança clara de tópico
    print("\nTESTE 1: Mudança clara de tópico")
    messages1 = [
        {'role': 'user', 'content': 'Qual é a capital do Brasil?'},
        {'role': 'assistant', 'content': 'A capital do Brasil é Brasília.'}
    ]
    new_message1 = "Me fale sobre as linguagens de programação mais populares."
    result1 = await mgr._detect_topic_change_with_ai(messages1, new_message1)
    print(f"Resultado: {result1}")
    
    # Teste 2: Continuação do mesmo tópico
    print("\nTESTE 2: Continuação do mesmo tópico")
    messages2 = [
        {'role': 'user', 'content': 'Qual é a capital do Brasil?'},
        {'role': 'assistant', 'content': 'A capital do Brasil é Brasília.'}
    ]
    new_message2 = "E qual é a população de Brasília?"
    result2 = await mgr._detect_topic_change_with_ai(messages2, new_message2)
    print(f"Resultado: {result2}")
    
    # Teste 3: Pergunta sobre a conversa em si
    print("\nTESTE 3: Pergunta sobre a conversa em si")
    messages3 = [
        {'role': 'user', 'content': 'Me conte sobre a história do Brasil.'},
        {'role': 'assistant', 'content': 'A história do Brasil começou com a chegada dos portugueses em 1500...'},
        {'role': 'user', 'content': 'Quem foi o primeiro presidente?'},
        {'role': 'assistant', 'content': 'O primeiro presidente do Brasil foi Deodoro da Fonseca.'}
    ]
    new_message3 = "O que falamos até agora na nossa conversa?"
    result3 = await mgr._detect_topic_change_with_ai(messages3, new_message3)
    print(f"Resultado: {result3}")

if __name__ == "__main__":
    asyncio.run(test_topic_detection()) 