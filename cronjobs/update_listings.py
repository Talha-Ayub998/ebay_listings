
import django
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the project directory to sys.path
sys.path.append(os.getenv('DJANGO_PROJECT_PATH'))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      os.getenv('DJANGO_SETTINGS_MODULE'))

django.setup()



from ebaysdk.trading import Connection as Trading
from ebaysdk.exception import ConnectionError
from listings.models import *
from helpers.generate_token import *
import logging
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fetch variables
appid = os.getenv('CLIENT_ID')
certid = os.getenv('CLIENT_SECRET')
devid = os.getenv('DEV_ID')
runame = os.getenv('RUNAME')

def update_listed_items():
    # Fetch items with status 'listed'
    listed_items = list(Item.objects.filter(
        status='listed').exclude(stock=0))[:10000]
    logger.info(f"Found {len(listed_items)} items with status 'listed'.")

    if not listed_items:
        return

    access_token = check_access_token()
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
            api = Trading(appid=appid, certid=certid, devid=devid,
                          token=access_token, domain={os.getenv('BASE_URL')}, config_file=None)

            # Send the request to update the items in bulk
            response = api.execute(
                'ReviseInventoryStatus', inventory_status_payload)
            logger.info(f"API response: {response.reply.Ack}")

            # Check if the update was successful
            if response.reply.Ack == 'Success':
                for item in chunk:
                    item.status = 'updated'
                    item.save()
                logger.info(f"Successfully updated {chunk}")
            else:
                logger.error(
                    f"Failed to update items: {response.reply.Errors}")

        except ConnectionError as e:
            logger.error(f"Error connecting to eBay API: {e}")

if __name__ == "__main__":
    update_listed_items()