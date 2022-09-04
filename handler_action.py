import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import event_source, EventBridgeEvent

from typing import Optional
import datetime
import pytz
from decimal import Decimal

import table
import api

logger = Logger()


ACTION_PERIOD = 5 * 60
DATETIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
EVENT_DATETIME_STR_FORMAT = '%Y-%m-%dT%H:%M:%S'

def get_service_account_token(current_timestamp,
                              client_id,
                              client_secret,
                              service_account,
                              private_key,
                              ):
    token_info = table.get_lw_access_token(service_account)
    if token_info is not None:
        if token_info["expired_at"] >= current_timestamp:
            return token_info["access_token"]

    scope = "bot"
    auth_api = api.ServiceAccountAuth(client_id,
                                      client_secret,
                                      service_account,
                                      private_key)
    res = auth_api.get_access_token(scope)

    token_info = {
        "user_id": service_account,
        "access_token": res["access_token"],
        "refresh_token": res["refresh_token"],
        "created_at": Decimal(current_timestamp),
        "expired_at": Decimal(current_timestamp + int(res["expires_in"])),
    }
    table.put_lw_access_token(token_info)

    return res["access_token"]


def main():
    current_time = datetime.datetime.now()
    from_time = current_time - datetime.timedelta(seconds=ACTION_PERIOD)
    until_time_str = current_time.strftime(DATETIME_STR_FORMAT)
    from_time_str = from_time.strftime(DATETIME_STR_FORMAT)

    logger.info("since: {}, until: {}".format(from_time_str, until_time_str))

    # Get settings
    settings = table.get_settings()

    # Get credential
    domain_id = os.environ.get("DOMAIN_ID")
    cred = table.get_lw_client_credential(domain_id)
    if cred == None:
        Exception("credentials are not set.")
    bot_id = cred["bot_id"]

    # Get service account token
    bot_access_token = get_service_account_token(current_time.timestamp(),
                                                 cred["client_id"],
                                                 cred["client_secret"],
                                                 cred["service_account"],
                                                 cred["private_key"]
                                                 )

    for s in settings:
        calendar_id = s["calendar_id"]
        user_id = s["user_id"]
        ifttt_event_id = s["ifttt_event_id"]
        ifttt_integration_key = s["ifttt_integration_key"]
        logger.info("calendar: {}, user: {}".format(calendar_id, user_id))

        # Get access token
        token_info = table.get_lw_access_token(user_id)
        access_token = token_info["access_token"]

        # API
        lwapi = api.LWApi(access_token)
        botapi = api.LWApi(bot_access_token)

        # Get calendar events
        res = lwapi.get_calendar_events(calendar_id, from_time_str, until_time_str, user_id)
        cal_events = []
        for e in res["events"]:
            for ec in e["eventComponents"]:
                # check starttime
                start_time = datetime.datetime.strptime(ec["start"]["dateTime"], EVENT_DATETIME_STR_FORMAT)
                logger.info(ec["start"]["dateTime"])
                start_time_jst = pytz.timezone(ec["start"]["timeZone"]).localize(start_time)
                logger.info("since {}: event_start: {} until: {}".format(from_time.timestamp(), start_time_jst.timestamp(), current_time.timestamp()))
                if start_time_jst.timestamp() > from_time.timestamp() and start_time_jst.timestamp() <= current_time.timestamp():
                    cal_events.append(ec)

        # Reqeust IFTTT
        iftttapi = api.IFTTTWebhook(ifttt_integration_key)
        for e in cal_events:
            logger.info(e)
            # Request
            r = iftttapi.request_webhook(ifttt_event_id, e)
            logger.info(r)
            # Bot request
            logger.info("Send bot message")
            msg = "Triggered event: {}".format(ifttt_event_id)
            botapi.send_text_message(bot_id, user_id, msg)


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
@event_source(data_class=EventBridgeEvent)
def lambda_handler(event: EventBridgeEvent, context: LambdaContext):
    logger.info(event)
    main()
