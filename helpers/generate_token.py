from urllib.parse import unquote, urlparse, parse_qs
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


def check_access_token():
    access_token = APIToken.objects.last().access_token
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

        token = APIToken.objects.last()
        token.access_token = access_token
        token.save()
        print(f"access_token updated")
        return access_token
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def get_authorization_code():
    """
    Retrieves the authorization code needed for obtaining access and refresh tokens.

    Returns:
        tuple: A tuple containing the base64 encoded credentials, the authorization code, and the redirect URI.
    """
    end_point = 'https://auth.sandbox.ebay.com/oauth2/authorize'
    scope = ' '.join([
        'https://api.ebay.com/oauth/api_scope/sell.inventory.readonly',
        'https://api.ebay.com/oauth/api_scope/sell.inventory',
        'https://api.ebay.com/oauth/api_scope/sell.account',
        'https://api.ebay.com/oauth/api_scope/sell.fulfillment',
        'https://api.ebay.com/oauth/api_scope/sell.marketing'
    ])
    url = f"{end_point}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"

    # You need to obtain this code_url by performing the actual OAuth flow
    code_url = 'https://auth.ebay.com/oauth2/ThirdPartyAuthSucessFailure?isAuthSuccessful=true&code=v%5E1.1%23i%5E1%23r%5E1%23f%5E0%23p%5E3%23I%5E3%23t%5EUl41XzExOjJBQTg1RTNBMkMyQjJGOTc2MUFDOEU5QkI2RDk5MjgyXzBfMSNFXjEyODQ%3D&expires_in=299'

    # Parse the URL to extract the 'code' parameter
    parsed_url = urlparse(code_url)
    query_params = parse_qs(parsed_url.query)
    code = query_params.get('code', [None])[0]
    code = unquote(code)

    # Encode client_id and client_secret
    encoded_credentials = base64.b64encode(
        f'{client_id}:{client_secret}'.encode()).decode()

    return encoded_credentials, code, redirect_uri


def get_user_access_and_refresh_token(encoded_credentials, code, redirect_uri):
    """
    Exchanges the authorization code for access and refresh tokens.

    Args:
        encoded_credentials (str): Base64 encoded client ID and client secret.
        code (str): Authorization code obtained from the OAuth flow.
        redirect_uri (str): Redirect URI used for the authorization request.

    Returns:
        tuple: A tuple containing the access token and refresh token if the request is successful, otherwise None.
    """
    token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {encoded_credentials}'
    }

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Parse JSON response
        response_data = response.json()

        # Extract tokens
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')

        # Check if tokens are present
        if not access_token or not refresh_token:
            raise ValueError(
                "Access token or refresh token not found in response.")

        return access_token, refresh_token

    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except ValueError as e:
        print(f"Value error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None
