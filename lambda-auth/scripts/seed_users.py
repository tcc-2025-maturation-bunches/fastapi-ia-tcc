"""
Script para criar usuários de teste no DynamoDB
Execute este script para popular o banco com usuários de exemplo
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.user_service import UserService


async def seed_users():
    """Cria usuários de teste no DynamoDB"""
    user_service = UserService()

    users = [
        {
            "username": "admin",
            "password": "admin123",
            "name": "Administrador",
            "email": "admin@example.com",
            "user_type": "admin",
        },
        {
            "username": "user1",
            "password": "user123",
            "name": "Usuário Teste 1",
            "email": "user1@example.com",
            "user_type": "user",
        },
        {
            "username": "user2",
            "password": "user456",
            "name": "Usuário Teste 2",
            "email": "user2@example.com",
            "user_type": "user",
        },
    ]

    print("🌱 Criando usuários de teste...")

    for user_data in users:
        try:
            user = await user_service.create_user(**user_data)
            print(f"✅ Usuário criado: {user.username} ({user.user_type})")
        except ValueError:
            print(f"⚠️  Usuário já existe: {user_data['username']}")
        except Exception as e:
            print(f"❌ Erro ao criar usuário {user_data['username']}: {e}")

    print("\n✨ Seed concluído!")
    print("\n📝 Credenciais de teste:")
    print("   Admin: admin / admin123")
    print("   User1: user1 / user123")
    print("   User2: user2 / user456")


if __name__ == "__main__":
    asyncio.run(seed_users())
