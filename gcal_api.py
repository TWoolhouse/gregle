import os
from pathlib import Path
import traceback
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google.auth.exceptions
from googleapiclient.discovery import Resource, build
from typing import Any, TypeAlias
from log import log

RES = Path(__file__).parent / "res"

def create_service(scopes: list[str], token_file: str, creds_file: str):
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
				return create_service(scopes, token_file, creds_file)
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				creds_file, scopes)
			log.error("Waiting for Authentication!")
			creds = flow.run_local_server(port=0)

		# Save the credentials for the next run
		with open(token_file, "w") as token:
			token.write(creds.to_json())

	return build("calendar", "v3", credentials=creds)

API: TypeAlias = Any
def calendar_service() -> API:
	return create_service([
		"https://www.googleapis.com/auth/calendar.readonly",
		"https://www.googleapis.com/auth/calendar.events",
	], str(RES / "token.json"), str(RES / "client_secret.json"))
