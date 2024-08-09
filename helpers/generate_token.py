from dotenv import load_dotenv
import requests
import base64
import os
from listings.models import *

load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
dev_id = os.getenv('DEV_ID')
redirect_uri = os.getenv('RUNAME')
refresh_token = os.getenv('REFRESH_TOKEN')


def generate_access_token_from_refresh_token():
    """
    Generates an access token using a refresh token.

    Args:
        encoded_credentials (str): Base64 encoded client ID and client secret.
        refresh_token (str): Refresh token to obtain the new access token.
        redirect_uri (str): Redirect URI used for the authorization request.

    Returns:
        str: Access token if the request is successful, otherwise None.
    """
    encoded_credentials = base64.b64encode(
        f'{client_id}:{client_secret}'.encode()).decode()
    token_url = f"https://{os.getenv('BASE_URL')}/identity/v1/oauth2/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_credentials}'
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'redirect_uri': redirect_uri,
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Parse JSON response
        response_data = response.json()

        # Extract tokens
        access_token = response_data.get('access_token')

        # Check if tokens are present
        if not access_token:
            raise ValueError("access_token not found in response.")

        return access_token

    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def check_access_token(access_token):
    # Set up headers for the request
    headers = {
        "Content-Type": "text/xml",
        "X-EBAY-API-SITEID": "0",  # Site ID for the US
        "X-EBAY-API-CALL-NAME": "GetTokenStatus",
        "X-EBAY-API-APP-NAME": client_id,
        "X-EBAY-API-DEV-NAME": dev_id,
        "X-EBAY-API-CERT-NAME": client_secret,
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967"  # eBay API version
    }

    # Set up the body for the request
    body = """<?xml version="1.0" encoding="utf-8"?>
        <GetTokenStatusRequest xmlns="urn:ebay:apis:eBLBaseComponents">
        <RequesterCredentials>
            <eBayAuthToken>{}</eBayAuthToken>
        </RequesterCredentials>
            <ErrorLanguage>en_US</ErrorLanguage>
            <WarningLevel>High</WarningLevel>
        </GetTokenStatusRequest>
        """.format(access_token)

    # eBay Trading API endpoint
    url = f"https://{os.getenv('BASE_URL')}/ws/api.dll"
    try:
        # Send the request
        response = requests.post(url, headers=headers, data=body)
        text = response.text
        if '<Ack>Success</Ack>' in text:
            return access_token

        access_token = generate_access_token_from_refresh_token()
        if not access_token:
            raise ValueError("access_token not found in response.")
        # APIToken.objects.last().update(access_token=access_token)
        return access_token
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None
