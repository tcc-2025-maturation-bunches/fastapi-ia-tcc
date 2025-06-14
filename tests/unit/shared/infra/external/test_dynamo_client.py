from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.shared.infra.external.dynamo.dynamo_client import DynamoClient, floats_to_decimals


class TestFloatsToDecimals:
    def test_convert_float_to_decimal(self):
        result = floats_to_decimals(3.14)
        assert isinstance(result, Decimal)
        assert result == Decimal("3.14")

    def test_convert_list_with_floats(self):
        input_list = [1.5, 2.7, 3]
        result = floats_to_decimals(input_list)
        assert isinstance(result, list)
        assert isinstance(result[0], Decimal)
        assert isinstance(result[1], Decimal)
        assert result[0] == Decimal("1.5")
        assert result[1] == Decimal("2.7")
        assert result[2] == 3

    def test_convert_dict_with_floats(self):
        input_dict = {"confidence": 0.95, "score": 85.5, "count": 10, "nested": {"value": 2.5}}
        result = floats_to_decimals(input_dict)
        assert isinstance(result, dict)
        assert isinstance(result["confidence"], Decimal)
        assert isinstance(result["score"], Decimal)
        assert result["confidence"] == Decimal("0.95")
        assert result["score"] == Decimal("85.5")
        assert result["count"] == 10
        assert isinstance(result["nested"]["value"], Decimal)

    def test_convert_datetime_to_isoformat(self):
        dt = datetime(2025, 6, 14, 12, 30, 0)
        result = floats_to_decimals(dt)
        assert isinstance(result, str)
        assert result == "2025-06-14T12:30:00"

    def test_convert_mixed_data_structure(self):
        input_data = {
            "results": [{"confidence": 0.95, "score": 85.5}, {"confidence": 0.87, "score": 92.3}],
            "timestamp": datetime(2025, 6, 14, 12, 30, 0),
            "metadata": {"processing_time": 150.75, "version": "1.0"},
        }
        result = floats_to_decimals(input_data)

        assert isinstance(result["results"][0]["confidence"], Decimal)
        assert isinstance(result["results"][1]["score"], Decimal)
        assert isinstance(result["timestamp"], str)
        assert isinstance(result["metadata"]["processing_time"], Decimal)
        assert result["metadata"]["version"] == "1.0"

    def test_no_conversion_needed(self):
        input_data = {"name": "test", "count": 5, "active": True}
        result = floats_to_decimals(input_data)
        assert result == input_data


class TestDynamoClient:
    @pytest.fixture
    def mock_boto3_table(self):
        with patch("boto3.resource") as mock_resource:
            mock_table = MagicMock()
            mock_client = MagicMock()
            mock_client.Table.return_value = mock_table
            mock_resource.return_value = mock_client
            yield mock_table

    def test_init_with_defaults(self, mock_boto3_table):
        client = DynamoClient()
        assert client.table_name == "fruit-detection-dev-results"
        assert client.region == "us-east-1"

    def test_init_with_custom_values(self, mock_boto3_table):
        client = DynamoClient(table_name="custom-table", region="us-west-2")
        assert client.table_name == "custom-table"
        assert client.region == "us-west-2"

    def test_convert_from_dynamo_item_simple(self, mock_boto3_table):
        client = DynamoClient()
        item = {"id": "test-id", "name": "test-name", "score": 95.5}
        result = client.convert_from_dynamo_item(item)
        assert result == item

    def test_convert_from_dynamo_item_with_timestamp(self, mock_boto3_table):
        client = DynamoClient()
        item = {"id": "test-id", "processing_timestamp": "2025-06-14T12:30:00", "other_field": "value"}
        result = client.convert_from_dynamo_item(item)
        assert isinstance(result["processing_timestamp"], datetime)
        assert result["other_field"] == "value"

    def test_convert_from_dynamo_item_with_json_fields(self, mock_boto3_table):
        client = DynamoClient()
        item = {
            "id": "test-id",
            "results": '{"confidence": 0.95, "class": "banana"}',
            "metadata": '{"source": "camera"}',
            "summary": '{"total": 5}',
        }
        result = client.convert_from_dynamo_item(item)
        assert isinstance(result["results"], dict)
        assert result["results"]["confidence"] == 0.95
        assert isinstance(result["metadata"], dict)
        assert isinstance(result["summary"], dict)

    def test_convert_from_dynamo_item_invalid_json(self, mock_boto3_table):
        client = DynamoClient()
        item = {"id": "test-id", "results": "invalid json string", "metadata": "another invalid json"}
        result = client.convert_from_dynamo_item(item)
        assert result["results"] == "invalid json string"
        assert result["metadata"] == "another invalid json"

    def test_convert_from_dynamo_item_empty(self, mock_boto3_table):
        client = DynamoClient()
        result = client.convert_from_dynamo_item({})
        assert result == {}

    def test_convert_from_dynamo_item_none(self, mock_boto3_table):
        client = DynamoClient()
        result = client.convert_from_dynamo_item(None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_put_item_success(self, mock_boto3_table):
        mock_boto3_table.put_item.return_value = None

        client = DynamoClient()
        item = {"pk": "test-pk", "sk": "test-sk", "confidence": 0.95}

        await client.put_item(item)

        mock_boto3_table.put_item.assert_called_once()
        call_args = mock_boto3_table.put_item.call_args[1]["Item"]
        assert call_args["pk"] == "test-pk"
        assert isinstance(call_args["confidence"], Decimal)

    @pytest.mark.asyncio
    async def test_put_item_error(self, mock_boto3_table):
        mock_boto3_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid item"}}, "PutItem"
        )

        client = DynamoClient()
        item = {"pk": "test-pk"}

        with pytest.raises(ClientError):
            await client.put_item(item)

    @pytest.mark.asyncio
    async def test_get_item_success(self, mock_boto3_table):
        mock_item = {"pk": "test-pk", "sk": "test-sk", "data": "test-data"}
        mock_boto3_table.get_item.return_value = {"Item": mock_item}

        client = DynamoClient()
        key = {"pk": "test-pk", "sk": "test-sk"}

        result = await client.get_item(key)

        assert result == mock_item
        mock_boto3_table.get_item.assert_called_once_with(Key=key)

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, mock_boto3_table):
        mock_boto3_table.get_item.return_value = {}

        client = DynamoClient()
        key = {"pk": "non-existent"}

        result = await client.get_item(key)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_item_error(self, mock_boto3_table):
        mock_boto3_table.get_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}}, "GetItem"
        )

        client = DynamoClient()
        key = {"pk": "test-pk"}

        result = await client.get_item(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_item_success(self, mock_boto3_table):
        mock_boto3_table.delete_item.return_value = None

        client = DynamoClient()
        key = {"pk": "test-pk", "sk": "test-sk"}

        result = await client.delete_item(key)

        assert result is True
        mock_boto3_table.delete_item.assert_called_once_with(Key=key)

    @pytest.mark.asyncio
    async def test_delete_item_error(self, mock_boto3_table):
        mock_boto3_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid key"}}, "DeleteItem"
        )

        client = DynamoClient()
        key = {"pk": "test-pk"}

        result = await client.delete_item(key)
        assert result is False

    @pytest.mark.asyncio
    async def test_query_items_basic(self, mock_boto3_table):
        mock_items = [
            {"pk": "test-pk", "sk": "item1", "data": "data1"},
            {"pk": "test-pk", "sk": "item2", "data": "data2"},
        ]
        mock_boto3_table.query.return_value = {"Items": mock_items}

        client = DynamoClient()

        result = await client.query_items("pk", "test-pk")

        assert len(result) == 2
        assert result[0]["sk"] == "item1"
        assert result[1]["sk"] == "item2"

    @pytest.mark.asyncio
    async def test_query_items_with_index(self, mock_boto3_table):
        mock_items = [{"gsi_pk": "test-gsi", "data": "gsi-data"}]
        mock_boto3_table.query.return_value = {"Items": mock_items}

        client = DynamoClient()

        await client.query_items("gsi_pk", "test-gsi", index_name="TestIndex")

        query_call = mock_boto3_table.query.call_args[1]
        assert query_call["IndexName"] == "TestIndex"

    @pytest.mark.asyncio
    async def test_query_items_with_pagination(self, mock_boto3_table):
        mock_items = [{"pk": "test-pk", "sk": "item1"}]
        mock_boto3_table.query.return_value = {"Items": mock_items}

        client = DynamoClient()
        last_key = {"pk": "last-pk", "sk": "last-sk"}

        await client.query_items("pk", "test-pk", limit=10, last_evaluated_key=last_key)

        query_call = mock_boto3_table.query.call_args[1]
        assert query_call["Limit"] == 10
        assert query_call["ExclusiveStartKey"] == last_key

    @pytest.mark.asyncio
    async def test_query_items_error(self, mock_boto3_table):
        mock_boto3_table.query.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid query"}}, "Query"
        )

        client = DynamoClient()

        with pytest.raises(ClientError):
            await client.query_items("pk", "test-pk")

    @pytest.mark.asyncio
    async def test_scan_basic(self, mock_boto3_table):
        mock_items = [{"pk": "item1", "type": "type1"}, {"pk": "item2", "type": "type1"}]
        mock_boto3_table.scan.return_value = {"Items": mock_items}

        client = DynamoClient()

        result = await client.scan()

        assert len(result) == 2
        mock_boto3_table.scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_with_filter(self, mock_boto3_table):
        mock_items = [{"pk": "item1", "type": "filtered"}]
        mock_boto3_table.scan.return_value = {"Items": mock_items}

        client = DynamoClient()

        await client.scan(
            filter_expression="#type = :type",
            expression_values={":type": "filtered"},
            expression_names={"#type": "type"},
        )

        scan_call = mock_boto3_table.scan.call_args[1]
        assert scan_call["FilterExpression"] == "#type = :type"
        assert scan_call["ExpressionAttributeValues"] == {":type": "filtered"}
        assert scan_call["ExpressionAttributeNames"] == {"#type": "type"}

    @pytest.mark.asyncio
    async def test_scan_with_index(self, mock_boto3_table):
        mock_items = [{"gsi_pk": "test"}]
        mock_boto3_table.scan.return_value = {"Items": mock_items}

        client = DynamoClient()

        await client.scan(index_name="TestIndex")

        scan_call = mock_boto3_table.scan.call_args[1]
        assert scan_call["IndexName"] == "TestIndex"

    @pytest.mark.asyncio
    async def test_batch_write_success(self, mock_boto3_table):
        mock_batch_writer = MagicMock()
        mock_boto3_table.batch_writer.return_value.__enter__.return_value = mock_batch_writer
        mock_boto3_table.batch_writer.return_value.__exit__.return_value = None

        client = DynamoClient()
        items = [{"pk": "item1", "data": "data1"}, {"pk": "item2", "data": "data2"}]
        delete_keys = [{"pk": "delete1"}]

        result = await client.batch_write(items, delete_keys)

        assert result is True
        assert mock_batch_writer.put_item.call_count == 2
        assert mock_batch_writer.delete_item.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_write_error(self, mock_boto3_table):
        mock_boto3_table.batch_writer.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Batch write failed"}}, "BatchWriteItem"
        )

        client = DynamoClient()
        items = [{"pk": "item1"}]

        result = await client.batch_write(items)
        assert result is False

    @pytest.mark.asyncio
    async def test_update_item_success(self, mock_boto3_table):
        updated_item = {"pk": "test-pk", "sk": "test-sk", "updated_field": "new_value"}
        mock_boto3_table.update_item.return_value = {"Attributes": updated_item}

        client = DynamoClient()
        key = {"pk": "test-pk", "sk": "test-sk"}
        update_expression = "SET updated_field = :val"
        expression_values = {":val": "new_value"}

        result = await client.update_item(key, update_expression, expression_values)

        assert result == updated_item
        update_call = mock_boto3_table.update_item.call_args[1]
        assert update_call["Key"] == key
        assert update_call["UpdateExpression"] == update_expression
        assert update_call["ReturnValues"] == "ALL_NEW"

    @pytest.mark.asyncio
    async def test_update_item_with_condition(self, mock_boto3_table):
        updated_item = {"pk": "test-pk", "counter": 5}
        mock_boto3_table.update_item.return_value = {"Attributes": updated_item}

        client = DynamoClient()
        key = {"pk": "test-pk"}
        update_expression = "SET counter = counter + :inc"
        expression_values = {":inc": 1}
        expression_names = {"#counter": "counter"}
        condition_expression = "attribute_exists(#counter)"

        await client.update_item(key, update_expression, expression_values, expression_names, condition_expression)

        update_call = mock_boto3_table.update_item.call_args[1]
        assert update_call["ExpressionAttributeNames"] == expression_names
        assert update_call["ConditionExpression"] == condition_expression

    @pytest.mark.asyncio
    async def test_update_item_error(self, mock_boto3_table):
        mock_boto3_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Condition failed"}}, "UpdateItem"
        )

        client = DynamoClient()
        key = {"pk": "test-pk"}

        with pytest.raises(ClientError):
            await client.update_item(key, "SET x = :val", {":val": "test"})

    @pytest.mark.asyncio
    async def test_query_with_pagination_success(self, mock_boto3_table):
        mock_items = [{"pk": "test-pk", "sk": "item1"}]
        last_key = {"pk": "test-pk", "sk": "item1"}
        mock_boto3_table.query.return_value = {
            "Items": mock_items,
            "LastEvaluatedKey": last_key,
            "Count": 1,
            "ScannedCount": 1,
        }

        client = DynamoClient()

        result = await client.query_with_pagination(
            "pk",
            "test-pk",
            limit=10,
            filter_expression="attribute_exists(#data)",
            expression_values={":status": "active"},
        )

        assert result["items"] == mock_items
        assert result["last_evaluated_key"] == last_key
        assert result["count"] == 1
        assert result["scanned_count"] == 1

    @pytest.mark.asyncio
    async def test_query_with_pagination_error(self, mock_boto3_table):
        mock_boto3_table.query.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid query"}}, "Query"
        )

        client = DynamoClient()

        with pytest.raises(ClientError):
            await client.query_with_pagination("pk", "test-pk")

    def test_get_table_info_success(self, mock_boto3_table):
        table_description = {
            "Table": {
                "TableName": "test-table",
                "TableStatus": "ACTIVE",
                "ItemCount": 100,
                "TableSizeBytes": 1024,
                "CreationDateTime": datetime(2025, 1, 1),
                "GlobalSecondaryIndexes": [
                    {
                        "IndexName": "TestIndex",
                        "KeySchema": [{"AttributeName": "gsi_pk", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
            }
        }
        mock_boto3_table.meta.client.describe_table.return_value = table_description

        client = DynamoClient()

        result = client.get_table_info()

        assert result["table_name"] == "test-table"
        assert result["table_status"] == "ACTIVE"
        assert result["item_count"] == 100
        assert result["table_size_bytes"] == 1024
        assert len(result["global_secondary_indexes"]) == 1
        assert result["global_secondary_indexes"][0]["index_name"] == "TestIndex"

    def test_get_table_info_error(self, mock_boto3_table):
        mock_boto3_table.meta.client.describe_table.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}}, "DescribeTable"
        )

        client = DynamoClient()

        result = client.get_table_info()
        assert result == {}

    @pytest.mark.asyncio
    async def test_scan_error(self, mock_boto3_table):
        mock_boto3_table.scan.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid scan"}}, "Scan"
        )

        client = DynamoClient()

        with pytest.raises(ClientError):
            await client.scan()

    @pytest.mark.asyncio
    async def test_scan_with_all_parameters(self, mock_boto3_table):
        mock_items = [{"pk": "item1", "status": "active"}]
        mock_boto3_table.scan.return_value = {"Items": mock_items}

        client = DynamoClient()
        last_key = {"pk": "last-item"}

        await client.scan(
            filter_expression="attribute_exists(#status)",
            expression_values={":status": "active"},
            expression_names={"#status": "status"},
            limit=50,
            last_evaluated_key=last_key,
            index_name="StatusIndex",
        )

        scan_call = mock_boto3_table.scan.call_args[1]
        assert scan_call["FilterExpression"] == "attribute_exists(#status)"
        assert scan_call["ExpressionAttributeValues"] == {":status": "active"}
        assert scan_call["ExpressionAttributeNames"] == {"#status": "status"}
        assert scan_call["Limit"] == 50
        assert scan_call["ExclusiveStartKey"] == last_key
        assert scan_call["IndexName"] == "StatusIndex"
