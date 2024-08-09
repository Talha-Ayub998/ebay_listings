from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from listings.models import *
import logging
from dotenv import load_dotenv
import os

load_dotenv()

# Fetch variables
appid = os.getenv('EBAY_APP_ID')
certid = os.getenv('EBAY_CERT_ID')
devid = os.getenv('EBAY_DEV_ID')
runame = os.getenv('EBAY_RUNAME')
access_token = APIToken.objects.last().access_token

logger = logging.getLogger(__name__)


def update_listed_items():
    # Fetch items with status 'listed'
    listed_items = list(Item.objects.filter(status='listed'))[:20000]

    # Split the items into chunks of 4
    for i in range(0, len(listed_items), 4):
        chunk = listed_items[i:i + 4]
        inventory_status_payload = {'InventoryStatus': []}

        for item in chunk:
            inventory_status_payload['InventoryStatus'].append({
                'ItemID': item.item_id,
                'Quantity': item.stock,
                'StartPrice': item.price,
            })

        try:

            # Initialize eBay Trading API connection
            # Use these variables in the API connection
            api = Trading(appid=appid, certid=certid, devid=devid,
                          token=access_token, domain='api.sandbox.ebay.com')

            # Send the request to update the items in bulk
            response = api.execute(
                'ReviseInventoryStatus', inventory_status_payload)

            # Check if the update was successful
            if response.reply.Ack == 'Success':
                for item in chunk:
                    item.status = 'updated'
                    item.save()
            else:
                print(f"Failed to update items: {response.reply.Errors}")

        except ConnectionError as e:
            print(f"Error connecting to eBay API: {e}")


# Call the function to update listed items
update_listed_items()
