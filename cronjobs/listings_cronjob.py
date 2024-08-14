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


import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
import logging
from django.db.models import Q
from listings.models import *
from helpers.generate_token import *
from cronjobs.update_listings import *
import re

# Configure logging
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_bulk_items_trading_api():
    """
    Creates or replaces inventory items in bulk based on data from the database using the eBay Trading API.
    """
    access_token = check_access_token()

    headers = {
        "Content-Type": "text/xml",
        "X-EBAY-API-SITEID": "100",  # Site ID for the US
        "X-EBAY-API-CALL-NAME": "AddItems",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "1193"  # eBay API version
    }

    # Fetch items from the database
    items = Item.objects.exclude(stock=0).filter(Q(status='not listed') | Q(status='error'))[:25000]

    if not items.exists():
        logger.info("No items found to list.")
        return

    # Process items in batches of 5
    batch_size = 5
    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start:batch_start + batch_size]

        add_items_request = ET.Element(
            'AddItemsRequest', xmlns="urn:ebay:apis:eBLBaseComponents")
        requester_credentials = ET.SubElement(
            add_items_request, 'RequesterCredentials')
        eBayAuthToken = ET.SubElement(requester_credentials, 'eBayAuthToken')
        eBayAuthToken.text = access_token
        version = ET.SubElement(add_items_request, 'Version')
        version.text = '1193'
        error_language = ET.SubElement(add_items_request, 'ErrorLanguage')
        error_language.text = 'en_US'
        warning_level = ET.SubElement(add_items_request, 'WarningLevel')
        warning_level.text = 'High'

        for index, item in enumerate(batch):
            try:
                add_item_request_container = ET.SubElement(
                    add_items_request, 'AddItemRequestContainer')
                message_id = ET.SubElement(
                    add_item_request_container, 'MessageID')
                message_id.text = str(index + 1)

                item_xml = ET.SubElement(add_item_request_container, 'Item')

                title = ET.SubElement(item_xml, 'Title')
                title.text = item.pdescription

                sku = ET.SubElement(item_xml, 'SKU')
                sku.text = str(item.sku)

                message = ET.SubElement(item_xml, 'Message')
                message.text = str(item.sku)

                description = ET.SubElement(item_xml, 'Description')
                description.text = (
                    f"Brand: {item.brand},\n"
                    f"Part Link: {item.partslink},\n"
                    f"OEM Number: {item.oem_number},\n\n"
                    f"{item.pdescription}"
                )

                primary_category = ET.SubElement(item_xml, 'PrimaryCategory')
                category_id = ET.SubElement(primary_category, 'CategoryID')
                category_id.text = '6755'

                category_mapping_allowed = ET.SubElement(
                    item_xml, 'CategoryMappingAllowed')
                category_mapping_allowed.text = 'true'

                site = ET.SubElement(item_xml, 'Site')
                site.text = 'eBayMotors'

                quantity = ET.SubElement(item_xml, 'Quantity')
                quantity.text = '1'

                start_price = ET.SubElement(item_xml, 'StartPrice')
                start_price.text = str(item.price)

                listing_duration = ET.SubElement(item_xml, 'ListingDuration')
                listing_duration.text = 'GTC'

                listing_type = ET.SubElement(item_xml, 'ListingType')
                listing_type.text = 'FixedPriceItem'

                dispatch_time_max = ET.SubElement(item_xml, 'DispatchTimeMax')
                dispatch_time_max.text = '3'

                shipping_details = ET.SubElement(item_xml, 'ShippingDetails')
                shipping_type = ET.SubElement(shipping_details, 'ShippingType')
                shipping_type.text = 'Flat'
                shipping_service_options = ET.SubElement(
                    shipping_details, 'ShippingServiceOptions')
                shipping_service_priority = ET.SubElement(
                    shipping_service_options, 'ShippingServicePriority')
                shipping_service_priority.text = '1'
                shipping_service = ET.SubElement(
                    shipping_service_options, 'ShippingService')
                shipping_service.text = 'FedExHomeDelivery'
                shipping_service_cost = ET.SubElement(
                    shipping_service_options, 'ShippingServiceCost')
                shipping_service_cost.text = '0.0'

                return_policy = ET.SubElement(item_xml, 'ReturnPolicy')
                returns_accepted_option = ET.SubElement(
                    return_policy, 'ReturnsAcceptedOption')
                returns_accepted_option.text = 'ReturnsAccepted'
                returns_within_option = ET.SubElement(
                    return_policy, 'ReturnsWithinOption')
                returns_within_option.text = 'Days_30'
                shipping_cost_paid_by_option = ET.SubElement(
                    return_policy, 'ShippingCostPaidByOption')
                shipping_cost_paid_by_option.text = 'Buyer'

                condition_id = ET.SubElement(item_xml, 'ConditionID')
                condition_id.text = '1000'

                # Add ConditionDisplayName element
                condition_display_name = ET.SubElement(item_xml, 'ConditionDisplayName')
                condition_display_name.text = 'New'

                country = ET.SubElement(item_xml, 'Country')
                country.text = 'US'

                currency = ET.SubElement(item_xml, 'Currency')
                currency.text = 'USD'

                postal_code = ET.SubElement(item_xml, 'PostalCode')
                postal_code.text = '60586'

                item_specifics = ET.SubElement(item_xml, 'ItemSpecifics')

                name_value_list_1 = ET.SubElement(
                    item_specifics, 'NameValueList')
                name_1 = ET.SubElement(name_value_list_1, 'Name')
                name_1.text = 'Title'
                value_1 = ET.SubElement(name_value_list_1, 'Value')
                value_1.text = item.part_name

                name_value_list_2 = ET.SubElement(
                    item_specifics, 'NameValueList')
                name_2 = ET.SubElement(name_value_list_2, 'Name')
                name_2.text = 'Publisher'
                value_2 = ET.SubElement(name_value_list_2, 'Value')
                value_2.text = item.brand

                name_value_list_3 = ET.SubElement(
                    item_specifics, 'NameValueList')
                name_3 = ET.SubElement(name_value_list_3, 'Name')
                name_3.text = 'Author'
                value_3 = ET.SubElement(name_value_list_3, 'Value')
                value_3.text = 'JK Rowling'

                name_value_list_4 = ET.SubElement(
                    item_specifics, 'NameValueList')
                name_4 = ET.SubElement(name_value_list_4, 'Name')
                name_4.text = 'Language'
                value_4 = ET.SubElement(name_value_list_4, 'Value')
                value_4.text = 'English'

                picture_details = ET.SubElement(item_xml, 'PictureDetails')
                gallery_type = ET.SubElement(picture_details, 'GalleryType')
                gallery_type.text = 'Gallery'
                picture_url = ET.SubElement(picture_details, 'PictureURL')
                picture_url.text = item.image_url or 'https://e7.pngegg.com/pngimages/325/220/png-clipart-ebay-logo-ebay-online-shopping-amazon-com-sales-ebay-logo-text-logo-thumbnail.png'

            except Exception as e:
                logger.error(f"Error processing item {item.sku}: {e}")

        request_body = ET.tostring(
            add_items_request, encoding='utf-8').decode('utf-8')
        xml_body = f"<?xml version='1.0' encoding='utf-8'?>\n{request_body}"
        xml_body = xml_body.strip()
        pretty_xml = xml.dom.minidom.parseString(
            xml_body).toprettyxml(indent="  ")

        logger.debug(pretty_xml)

        # URL for the eBay Trading API
        url = f"https://{os.getenv('BASE_URL')}/ws/api.dll"

        # Make the POST request
        response = requests.post(url, headers=headers, data=xml_body)
        response_text = response.text

        if '<Ack>Success</Ack>' in response_text or '<ItemID>' in response_text:
            logger.info(
                f"Successfully listed batch starting at item {batch_start}.")

            # Regular expression patterns to find ItemID and CorrelationID
            item_id_pattern = re.compile(r'<ItemID>(\d+)</ItemID>')
            message_id_pattern = re.compile(
                r'<CorrelationID>(\d+)</CorrelationID>')

            # Find all matches in the response
            item_ids = item_id_pattern.findall(response_text)
            message_ids = message_id_pattern.findall(response_text)

            # Ensure the number of item_ids matches the number of message_ids
            if len(item_ids) != len(message_ids):
                logger.error(
                    "Mismatch between the number of ItemIDs and CorrelationIDs found.")
            else:
                for item_id, message_id in zip(item_ids, message_ids):
                    try:
                        # Get the SKU from the batch using the message_id
                        sku = batch[int(message_id) - 1].sku
                        # Save ItemID to the corresponding SKU in the database
                        Item.objects.filter(sku=sku).update(
                            item_id=item_id, status='listed')
                        logger.info(f"ItemID {item_id} updated for SKU {sku}")
                    except IndexError:
                        debug_info = f"MessageID {message_id} is out of range for the batch"
                        Item.objects.filter(sku=sku).update(
                            status='error', debug_info=debug_info)
                        logger.error(debug_info)
                    except Exception as e:
                        debug_info = f"Error updating SKU {sku} with ItemID {item_id}: {e}"
                        Item.objects.filter(sku=sku).update(
                            status='error', debug_info=debug_info)
                        logger.error(debug_info)
        else:
            logger.error(
                f"Failed to list batch starting at item {batch_start}. Response: {response.status_code} {response.text}")


if __name__ == "__main__":
    create_bulk_items_trading_api()
    update_listed_items()


# <ItemSpecifics >
#            <NameValueList >
#                 <Name > Type < /Name >
#                 <Value > Fender Liner < /Value >
#             </NameValueList >
#             <NameValueList >
#                 <Name > Brand</Name>
#                 <Value > ACCORD 94-97 FRONT FENDER LINER</Value>
#             </NameValueList >
# </ItemSpecifics>