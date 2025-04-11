#!/bin/bash

echo "==============================================="
echo "  Reiniciando ambiente de dependências"
echo "==============================================="

# Verifica se pip está instalado
if ! command -v pip &> /dev/null; then
    echo "❌ pip não encontrado. Por favor, instale o Python e o pip."
    exit 1
fi

# Desinstala todas as dependências atuais (exceto pip e setuptools)
echo "🧹 Desinstalando dependências atuais..."
pip freeze | grep -v "^-e" | grep -v "pip" | grep -v "setuptools" | xargs pip uninstall -y

# Limpa o cache do pip
echo "🧹 Limpando cache do pip..."
pip cache purge

# Atualiza o pip para a versão mais recente
echo "🔄 Atualizando pip..."
pip install --upgrade pip

# Reinstala as dependências do requirements.txt
echo "📦 Instalando dependências do requirements.txt..."
pip install -r requirements.txt

echo "✅ Dependências reinstaladas com sucesso!"
echo "===============================================" 