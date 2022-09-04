import requests
import json
import jwt
from datetime import datetime
import urllib.parse


class UserAccountAuth:
    BASE_URI = "https://auth.worksmobile.com/oauth2/v2.0"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def create_redirect_uri(self, host):
        path = "/redirect"
        return "https://{}{}".format(host, path)

    def create_auth_url(self, scope, redirect_uri):
        query_params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "response_type": "code",
            "state": "state",
        }
        query_str = urllib.parse.urlencode(query_params)

        return "{}/authorize?{}".format(self.BASE_URI, query_str)

    def get_access_token(self, auth_code):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        params = {
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        form_data = params
        url = "{}/token".format(self.BASE_URI)

        r = requests.post(url=url, data=form_data, headers=headers)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e

        return r.json()


class ServiceAccountAuth:
    BASE_URI = "https://auth.worksmobile.com/oauth2/v2.0"

    def __init__(self, client_id, client_secret, service_account, private_key):
        self.client_id = client_id
        self.client_secret = client_secret
        self.service_account = service_account
        self.private_key = private_key

    def __get_jwt(self) -> str:
        current_time = datetime.now().timestamp()
        iss = self.client_id
        sub = self.service_account
        iat = current_time
        exp = current_time + (60 * 60) # 1 hour

        jws = jwt.encode(
            {
                "iss": iss,
                "sub": sub,
                "iat": iat,
                "exp": exp
            }, self.private_key, algorithm="RS256")

        return jws

    def get_access_token(self, scope):
        # Get JWT
        jwt = self.__get_jwt()

        # Get Access Token
        url = '{}/token'.format(self.BASE_URI)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        params = {
            "assertion": jwt,
            "grant_type": urllib.parse.quote("urn:ietf:params:oauth:grant-type:jwt-bearer"),
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": scope,
        }

        form_data = params

        r = requests.post(url=url, data=form_data, headers=headers)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise

        return r.json()


class LWApi:
    BASE_URI = "https://www.worksapis.com/v1.0"

    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
          'Content-Type' : 'application/json',
          'Authorization' : "Bearer {}".format(access_token)
        }

    def get_user(self, user_id="me"):
        path = "/users/{}".format(user_id)
        url = "{}{}".format(self.BASE_URI, path)

        r = requests.get(url=url, headers=self.headers)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e

        return r.json()

    def post_calendar(self, calendar_name, description=""):
        path = "/calendars"
        url = "{}{}".format(self.BASE_URI, path)

        body = {
            "calendarName": calendar_name,
            "description": description
        }
        body_data = json.dumps(body)
        r = requests.post(url=url, headers=self.headers, data=body_data)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e

        return r.json()

    def get_calendar_events(self, calendar_id, from_datetime, until_datetime, user_id="me"):
        path = "/users/{}/calendars/{}/events".format(user_id, calendar_id)
        url = "{}{}".format(self.BASE_URI, path)

        params = {
            "fromDateTime": from_datetime,
            "untilDateTime": until_datetime,
        }

        r = requests.get(url=url, headers=self.headers, params=params)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e

        return r.json()

    def send_text_message(self, bot_id, user_id, text):
        path = "/bots/{}/users/{}/messages".format(bot_id, user_id)
        url = "{}{}".format(self.BASE_URI, path)

        body = {
            "content": {
                "type": "text",
                "text": text
            }
        }

        body_data = json.dumps(body)
        r = requests.post(url=url, headers=self.headers, data=body_data)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e


class IFTTTWebhook:
    BASE_URI = "https://maker.ifttt.com/trigger/{}/json/with/key/{}"

    def __init__(self,integration_key):
        self.integration_key = integration_key

    def request_webhook(self, event_id, body):
        url = self.BASE_URI.format(event_id, self.integration_key)

        body_data = json.dumps(body)
        r = requests.post(url=url,data=body_data)

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise e

        return r.text
