#!/usr/bin/env python
"""
Script para reinstalar dependências do projeto MPC.
Resolve conflitos de dependências e reinstala pacotes necessários.
"""

import os
import sys
import subprocess
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.append(str(root_dir))

def run_command(command):
    """Executa um comando shell e retorna a saída."""
    print(f"Executando: {command}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    
    print(stdout)
    if stderr:
        print(f"ERRO: {stderr}")
    
    return process.returncode

def reinstall_dependencies():
    """Reinstala as dependências do projeto."""
    print("=== Reinstalando dependências do projeto MPC ===")
    
    # Atualiza pip
    print("\n1. Atualizando pip...")
    run_command("pip install --upgrade pip")
    
    # Limpa cache do pip
    print("\n2. Limpando cache do pip...")
    run_command("pip cache purge")
    
    # Remove pacotes problemáticos
    print("\n3. Removendo pacotes problemáticos...")
    run_command("pip uninstall -y mistralai httpx openai")
    
    # Instala pacotes em ordem específica
    print("\n4. Instalando httpx com versão compatível...")
    run_command("pip install httpx>=0.25.2,<0.26.0")
    
    print("\n5. Instalando mistralai...")
    run_command("pip install mistralai==0.0.12")
    
    print("\n6. Instalando openai...")
    run_command("pip install openai==1.12.0")
    
    # Instala o restante dos pacotes
    print("\n7. Instalando demais dependências...")
    requirements_path = os.path.join(root_dir, "requirements.txt")
    run_command(f"pip install -r {requirements_path}")
    
    print("\n=== Verificação final ===")
    run_command("pip list | grep -E 'mistralai|httpx|openai'")
    
    print("\nReinstalação concluída!")

if __name__ == "__main__":
    reinstall_dependencies() 