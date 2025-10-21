import logging
from typing import Any, Dict, Optional

from fruit_detection_shared.infra.external import DynamoClient

from src.app.config import settings

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self, dynamo_client: Optional[DynamoClient] = None):
        self.dynamo_client = dynamo_client or DynamoClient(table_name=settings.DYNAMODB_TABLE_NAME)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"Criando usuário {user_data.get('username')}")
            return await self.dynamo_client.put_item(user_data)
        except Exception as e:
            logger.exception(f"Erro ao criar usuário: {e}")
            raise

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            items = await self.dynamo_client.query_items(key_name="username", key_value=username)
            if not items:
                logger.info(f"Usuário não encontrado: {username}")
                return None
            return items[0]
        except Exception as e:
            logger.exception(f"Erro ao buscar usuário por username: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            items = await self.dynamo_client.query_items(
                key_name="user_id", key_value=user_id, index_name="user_id-index"
            )
            if not items:
                logger.info(f"Usuário não encontrado: {user_id}")
                return None
            return items[0]
        except Exception as e:
            logger.exception(f"Erro ao buscar usuário por id: {e}")
            raise

    async def update_user(self, username: str, update_data: Dict[str, Any]) -> None:
        try:
            key = {"username": username}
            update_expressions = []
            expression_values = {}
            expression_names = {}
            for field, value in update_data.items():
                update_expressions.append(f"#{field} = :{field}")
                expression_names[f"#{field}"] = field
                expression_values[f":{field}"] = value
            update_expression = "SET " + ", ".join(update_expressions)
            await self.dynamo_client.update_item(
                key=key,
                update_expression=update_expression,
                expression_values=expression_values,
                expression_names=expression_names if expression_names else None,
            )
            logger.info(f"Usuário atualizado: {username}")
        except Exception as e:
            logger.exception(f"Erro ao atualizar usuário: {e}")
            raise

    async def delete_user(self, username: str) -> None:
        try:
            key = {"username": username}
            await self.dynamo_client.delete_item(key)
            logger.info(f"Usuário deletado: {username}")
        except Exception as e:
            logger.exception(f"Erro ao deletar usuário: {e}")
            raise
