import os
from typing import Any, TypeAlias

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .. import path as PATH
from ..log import log

API: TypeAlias = Any
Calendar: TypeAlias = str


def _scope_creds(scopes: list[str], token_file: str, creds_file: str):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError as e:
                log.warning("Google API Credentials Expired!", exc_info=e)
                os.remove(token_file)
                return _scope_creds(scopes, token_file, creds_file)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, scopes)
            log.info("Waiting for Authentication!")
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return creds


def calendar() -> API:
    log.info("Connecting to Calendar Service")
    creds = _scope_creds(
        [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        str(PATH.CACHE / "token.json"),
        str(PATH.RES / "client_secret.json"),
    )
    return build("calendar", "v3", credentials=creds)
