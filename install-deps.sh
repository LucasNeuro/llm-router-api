#!/bin/bash
# Script para testar a instalação de dependências em um ambiente isolado

echo "====== Criando ambiente virtual para testes ======"
python -m venv .venv.test
source .venv.test/bin/activate || . .venv.test/Scripts/activate

echo "====== Atualizando pip ======"
pip install --upgrade pip
pip cache purge

echo "====== Instalando dependências na ordem correta ======"
# Primeiro mistralai para estabelecer as dependências de httpx
pip install mistralai==0.0.12

# Depois os outros pacotes
pip install openai==1.12.0
pip install supabase==1.0.3
pip install anthropic==0.18.1

# Por fim, o resto dos requerimentos com --no-deps para evitar conflitos
pip install -r requirements.txt

echo "====== Verificando versões instaladas ======"
pip list | grep httpx
pip list | grep mistralai
pip list | grep supabase
pip list | grep anthropic
pip list | grep openai

echo "====== Teste completo ======"
# Desative o ambiente virtual
deactivate

echo "Para ativar o ambiente de teste, execute: source .venv.test/bin/activate (Linux/Mac) ou .venv.test/Scripts/activate (Windows)" 