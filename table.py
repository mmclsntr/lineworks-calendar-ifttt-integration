import os
import boto3
import botocore.exceptions
from typing import Optional


# DynamoDB
def get_item(table_name: str, key: dict) -> Optional[dict]:
    """
    Get item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.get_item(
        Key=key
    )

    if "Item" in response:
        return response['Item']
    else:
        return None


def get_items(table_name: str) -> list:
    """
    Get items from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.scan()

    if "Items" in response:
        return response['Items']
    else:
        return []


def put_item(table_name: str, item: dict):
    """
    Put item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    try:
        table.put_item(
            Item=item,
        )
    except botocore.exceptions.ClientError as e:
        raise


def put_item_w_condition(table_name: str, item: dict, condition_expression: str, expression_attribute_values: dict):
    """
    Put item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    try:
        table.put_item(
            Item=item,
            ConditionExpression=condition_expression,
            ExpressionAttributeValues=expression_attribute_values,
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # 条件NG
            pass
        else:
            raise


# Table
def get_lw_client_credential(domain_id: str) -> Optional[dict]:
    table_name = os.environ["TABLE_LW_CLIENT_CRED"]
    return get_item(table_name, {"domain_id": domain_id})


def get_lw_access_token(user_id: str) -> Optional[dict]:
    table_name = os.environ["TABLE_LW_TOKEN"]
    return get_item(table_name, {"user_id": user_id})


def put_lw_access_token(info: dict):
    table_name = os.environ["TABLE_LW_TOKEN"]
    put_item(table_name, info)


def put_setting(setting: dict):
    table_name = os.environ["TABLE_SETTIG"]
    put_item(table_name, setting)


def get_settings():
    table_name = os.environ["TABLE_SETTIG"]
    return get_items(table_name)
