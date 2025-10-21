#!/usr/bin/env python3
"""
Script para debugar a instalação do shared-libs
"""
import sys
import os
from pathlib import Path

def debug_installation():
    print("🔍 Debugando instalação do shared-libs...")
    print()
    
    # 1. Verificar paths do Python
    print("📁 Python paths:")
    for path in sys.path:
        print(f"  - {path}")
    print()
    
    # 2. Verificar se o módulo está instalado
    print("📦 Pacotes instalados com 'fruit':")
    try:
        import pkg_resources
        for pkg in pkg_resources.working_set:
            if 'fruit' in pkg.project_name.lower():
                print(f"  - {pkg.project_name} v{pkg.version} em {pkg.location}")
    except Exception as e:
        print(f"  Erro: {e}")
    print()
    
    # 3. Verificar estrutura de diretórios
    shared_libs_path = Path("shared-libs")
    if shared_libs_path.exists():
        print("📂 Estrutura do shared-libs:")
        print(f"  shared-libs/ existe: {shared_libs_path.exists()}")
        
        src_path = shared_libs_path / "src"
        print(f"  src/ existe: {src_path.exists()}")
        
        if src_path.exists():
            for item in src_path.iterdir():
                print(f"    - {item.name}")
                
        fruit_path = src_path / "fruit_detection_shared"
        print(f"  fruit_detection_shared/ existe: {fruit_path.exists()}")
        
        if fruit_path.exists():
            init_file = fruit_path / "__init__.py"
            print(f"  __init__.py existe: {init_file.exists()}")
            
            print("  Conteúdo do diretório:")
            for item in fruit_path.iterdir():
                print(f"    - {item.name}")
    else:
        print("❌ Diretório shared-libs não encontrado!")
    print()
    
    # 4. Verificar setup.py
    setup_file = shared_libs_path / "setup.py"
    print(f"📄 setup.py existe: {setup_file.exists()}")
    if setup_file.exists():
        with open(setup_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print("  Conteúdo relevante:")
            for line in content.split('\n'):
                if any(keyword in line for keyword in ['name=', 'packages=', 'package_dir=']):
                    print(f"    {line.strip()}")
    print()
    
    # 5. Tentar imports específicos
    print("🧪 Testando imports:")
    
    # Teste 1: Import direto
    try:
        import fruit_detection_shared
        print("  ✅ import fruit_detection_shared - OK")
        print(f"     Localização: {fruit_detection_shared.__file__}")
    except ImportError as e:
        print(f"  ❌ import fruit_detection_shared - ERRO: {e}")
    
    # Teste 2: Import com sys.path
    try:
        current_dir = Path.cwd()
        shared_src = current_dir / "shared-libs" / "src"
        if shared_src.exists() and str(shared_src) not in sys.path:
            sys.path.insert(0, str(shared_src))
            print(f"  📁 Adicionado ao sys.path: {shared_src}")
            
        import fruit_detection_shared
        print("  ✅ import com sys.path - OK")
    except ImportError as e:
        print(f"  ❌ import com sys.path - ERRO: {e}")
    
    # Teste 3: Import de submódulos
    try:
        from fruit_detection_shared.domain.entities import CombinedResult
        print("  ✅ import CombinedResult - OK")
    except ImportError as e:
        print(f"  ❌ import CombinedResult - ERRO: {e}")

if __name__ == "__main__":
    debug_installation()