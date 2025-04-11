#!/usr/bin/env python
"""
Script para diagnosticar conflitos de dependências em pacotes Python.
"""

import sys
import subprocess
import json
from pprint import pprint

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
    
    if stdout:
        print(stdout)
    if stderr:
        print(f"ERRO: {stderr}")
    
    return stdout, stderr, process.returncode

def check_package_deps(package_name):
    """Verifica as dependências de um pacote específico."""
    print(f"==== Verificando dependências de {package_name} ====")
    
    # Instala pip-check para análise de dependências
    run_command("pip install pip-check")
    
    # Verifica dependências com pip show
    stdout, _, _ = run_command(f"pip show {package_name}")
    requires = None
    for line in stdout.splitlines():
        if line.startswith("Requires:"):
            requires = line.split(":", 1)[1].strip()
            break
            
    if requires:
        print(f"Dependências: {requires}")
        deps = [dep.strip() for dep in requires.split(",")]
        return deps
    else:
        print(f"Nenhuma dependência encontrada para {package_name}")
        return []

def analyze_conflicts():
    """Analisa conflitos entre pacotes importantes."""
    packages = ["mistralai", "openai", "supabase", "anthropic"]
    
    # Coletar dependências de cada pacote
    deps_map = {}
    for pkg in packages:
        deps = check_package_deps(pkg)
        deps_map[pkg] = deps
    
    # Verificar conflitos de httpx
    httpx_deps = []
    for pkg, deps in deps_map.items():
        for dep in deps:
            if dep.startswith("httpx"):
                print(f"{pkg} requer {dep}")
                httpx_deps.append((pkg, dep))
    
    if httpx_deps:
        print("\n==== Análise de Conflitos ====")
        if len(httpx_deps) > 1:
            print("Conflitos potenciais de httpx detectados:")
            for pkg, dep in httpx_deps:
                print(f"  - {pkg}: {dep}")
        else:
            print("Nenhum conflito de httpx detectado entre os pacotes.")
    
    # Recomendações
    print("\n==== Recomendações ====")
    print("1. Instale httpx na versão que satisfaça todos os requisitos")
    print("2. Instale os pacotes principais com --no-dependencies")
    print("3. Instale manualmente as demais dependências necessárias")
    print("4. Instale os demais pacotes normalmente")

if __name__ == "__main__":
    print("==== Diagnóstico de Conflitos de Dependências ====")
    
    # Verificar versão do pip
    run_command("pip --version")
    
    # Verificar pacotes instalados
    run_command("pip list")
    
    # Analisar conflitos
    analyze_conflicts()
    
    print("\n==== Diagnóstico completo ====") 