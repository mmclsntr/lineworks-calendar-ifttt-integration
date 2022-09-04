import os
import urllib.parse

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver, Response, content_types
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from jinja2 import Environment, FileSystemLoader
from typing import Optional
import datetime
from decimal import Decimal

import table
import api

env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'), encoding='utf8'))

logger = Logger()
app = APIGatewayHttpResolver()


@app.get("/")
def get_index():
    logger.info(app.current_event.headers)
    logger.info(app.current_event.query_string_parameters)

    domain_id = os.environ.get("DOMAIN_ID")

    # get credential
    cred = table.get_lw_client_credential(domain_id)
    auth = api.UserAccountAuth(cred["client_id"], cred["client_secret"])
    if cred == None:
        Exception("credentials are not set.")

    host = app.current_event.get_header_value("host")
    redirect_uri = auth.create_redirect_uri(host)

    logger.info(domain_id)
    logger.info(redirect_uri)

    scope = "user.email.read,calendar"
    auth_url = auth.create_auth_url(scope, redirect_uri)

    logger.info(auth_url)

    template = env.get_template('index.html')
    html = template.render(auth_url=auth_url, redirect_url=redirect_uri)

    return Response(
        status_code=200,
        content_type=content_types.TEXT_HTML,
        body=html,
    )


@app.get("/redirect")
def get_redirect():
    logger.info(app.current_event.headers)
    logger.info(app.current_event.query_string_parameters)

    domain_id = os.environ.get("DOMAIN_ID")

    auth_code = app.current_event.get_query_string_value("code")

    # get credential
    cred = table.get_lw_client_credential(domain_id)

    current_time = datetime.datetime.now().timestamp()
    # Get token
    auth = api.UserAccountAuth(cred["client_id"], cred["client_secret"])
    res = auth.get_access_token(auth_code)
    logger.info(res)

    # Get user
    lwapi = api.LWApi(res["access_token"])
    user = lwapi.get_user()
    logger.info(user)

    user_id = user["userId"]

    token_info = {
        "user_id": user["userId"],
        "access_token": res["access_token"],
        "refresh_token": res["refresh_token"],
        "created_at": Decimal(current_time),
        "expired_at": Decimal(current_time + int(res["expires_in"])),
    }
    table.put_lw_access_token(token_info)

    return Response(
        status_code=302,
        content_type=content_types.TEXT_HTML,
        body=None,
        headers={
            "Location": "/settings?user_id={}".format(user_id)
        },
    )


@app.get("/settings")
def get_setting():
    # get user
    logger.info(app.current_event.headers)
    logger.info(app.current_event.query_string_parameters)

    user_id = app.current_event.get_query_string_value("user_id")

    # render
    template = env.get_template('settings.html')
    html = template.render(user_id=user_id)

    return Response(
        status_code=200,
        content_type=content_types.TEXT_HTML,
        body=html,
    )


@app.post("/settings/submit")
def get_setting_submit():
    logger.info(app.current_event.headers)
    logger.info(app.current_event.body)
    logger.info(app.current_event.decoded_body)
    logger.info(app.current_event.query_string_parameters)

    # get params
    param_str = app.current_event.decoded_body
    params = urllib.parse.parse_qs(param_str)
    logger.info(params)
    user_id = params["user_id"][0]
    event_id = params["event_id"][0]
    integration_key = params["integration_key"][0]
    description = params["description"][0]

    calendar_name = "integration: {}".format(event_id)

    # Get access token
    token_info = table.get_lw_access_token(user_id)

    # Create calendar
    lwapi = api.LWApi(token_info["access_token"])
    calendar = lwapi.post_calendar(calendar_name, description)
    logger.info(calendar)

    calendar_id = calendar["calendarId"]

    # Put setting
    setting = {
        "calendar_id": calendar_id,
        "user_id": user_id,
        "ifttt_integration_key": integration_key,
        "ifttt_event_id": event_id,
    }
    table.put_setting(setting)

    # render
    template = env.get_template('settings_submit.html')
    html = template.render()

    return Response(
        status_code=200,
        content_type=content_types.TEXT_HTML,
        body=html,
    )


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info(event)
    return app.resolve(event, context)
