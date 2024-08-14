import hashlib
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

import pandas as pd
from django.db import transaction
from listings.models import *
from helpers.s3 import S3Service


bucket_name = os.getenv('S3_BUCKET')
s3_client = S3Service(
    region_name=os.getenv('REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)


def xlsx_to_csv(xlsx_file, csv_file):
    """
    Convert an Excel file to a CSV file after preprocessing the data.

    Args:
        xlsx_file (str): Path to the input Excel file.
        csv_file (str): Path to the output CSV file.
    """
    try:
        # Read the Excel file
        df = pd.read_excel(xlsx_file, engine='openpyxl')

        # Preprocess the dataframe
        df = preprocess_dataframe(df)

        # Save as CSV file
        df.to_csv(csv_file, index=False)
    except Exception as e:
        raise Exception(f"Failed to convert {xlsx_file} to CSV: {e}")


def preprocess_dataframe(df):
    # Add an empty row
    empty_row = pd.DataFrame([{}], columns=df.columns)
    df = pd.concat([df, empty_row], ignore_index=True)

    # Strip any leading/trailing spaces from column names
    df.columns = df.columns.str.strip()

    # Drop rows with NaN values in essential columns
    essential_columns = ['SKU', 'PART_NAME']
    df = df.dropna(subset=essential_columns)

    # Drop duplicate rows based on all columns
    df = df.drop_duplicates()

    # Convert numeric columns that may have .0 suffix to integers
    numeric_columns = ['SKU', 'STOCK_TOTAL']
    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column], errors='coerce').fillna(0).astype(int)

    # Remove leading and trailing spaces from all string columns
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(
        x, str) else x) if col.dtype == "object" else col)

    # Drop rows with default values in essential columns
    df = df[(df['SKU'] != 0) & (df['PART_NAME'].str.strip() != '')]

    return df


def save_csv_to_db(csv_file, chunk_size=10000, batch_size=1000):
    """Saves CSV data to the database in chunks.

    Args:
        csv_file (str): Path to the CSV file.
        chunk_size (int, optional): Number of rows to read at a time. Defaults to 10000.
        batch_size (int, optional): Number of items to bulk create in each transaction. Defaults to 1000.
    """
    try:
        for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
            chunk = preprocess_dataframe(chunk)
            items_to_create = []
            items_to_update = []
            existing_items = {item.sku: item for item in Item.objects.filter(
                sku__in=chunk['SKU'].tolist())}

            for index, row in chunk.iterrows():
                sku = str(row.get('SKU', ''))
                if sku in existing_items:
                    existing_item = existing_items[sku]
                    if (existing_item.price != float(row.get('B2B_PRICE15', 0.0)) or existing_item.stock != int(float(row.get('STOCK_TOTAL', 0)))):
                        existing_item.price = float(row.get('B2B_PRICE15', 0.0))
                        existing_item.stock = int(float(row.get('STOCK_TOTAL', 0)))
                        if existing_item.status == 'updated':
                            existing_item.status = 'listed'
                        items_to_update.append(existing_item)
                else:
                    item = Item(
                        sku=sku,
                        brand=str(row.get('BRAND', '')),
                        part_name=str(row.get('PART_NAME', '')),
                        partslink=str(row.get('PARTSLINK', '')),
                        oem_number=str(row.get('OEM_NUMBER', '')),
                        category_id=str(row.get('CATEGORY_ID', '')),
                        price=float(row.get('B2B_PRICE15', 0.0)),
                        shipping_revenue18=float(
                            row.get('SHIPPINGREVENUE18', 0.0)),
                        handling_revenue18=float(
                            row.get('HANDLINGREVENUE18', 0.0)),
                        stock_va=int(float(row.get('STOCK_VA', 0))),
                        stock_il=int(float(row.get('STOCK_IL', 0))),
                        stock_las1=int(float(row.get('STOCK_LAS1', 0))),
                        stock_peru=int(float(row.get('STOCK_PERU', 0))),
                        stock_gpt=int(float(row.get('STOCK_GPT', 0))),
                        stock_jax=int(float(row.get('STOCK_JAX', 0))),
                        stock=int(float(row.get('STOCK_TOTAL', 0))),
                        pdescription=str(row.get('PDESCRIPTION', '')),
                    )
                    items_to_create.append(item)
                if len(items_to_create) >= batch_size:
                    with transaction.atomic():
                        Item.objects.bulk_create(
                            items_to_create, ignore_conflicts=True)
                    items_to_create = []
                if len(items_to_update) >= batch_size:
                    with transaction.atomic():
                        Item.objects.bulk_update(
                            items_to_update, ['price', 'stock', 'status'])
                    items_to_update = []

            if items_to_create:
                with transaction.atomic():
                    Item.objects.bulk_create(
                        items_to_create, ignore_conflicts=True)

            if items_to_update:
                with transaction.atomic():
                    Item.objects.bulk_update(
                        items_to_update, ['price', 'stock', 'status'])

    except Exception as e:
        print(row, e)


def generate_file_hash(file_path):
    """Generate a SHA-256 hash for the file content."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    local_xlsx_file_template = "/tmp/{}_latest_file.xlsx"
    local_csv_file_template = "/tmp/{}_latest_file.csv"

    # Get the latest file names from S3
    latest_file_keys = s3_client.get_previous_day_files(bucket_name)
    if not latest_file_keys:
        return

    for latest_file_key in latest_file_keys:
        latest_file_name = latest_file_key.split('/')[-1]
        local_xlsx_file = local_xlsx_file_template.format(latest_file_name)
        local_csv_file = local_csv_file_template.format(latest_file_name)

        # Download the latest xlsx file from S3
        s3_client.download_from_s3(
            latest_file_key, bucket_name, local_xlsx_file)

        # Generate the hash for the downloaded file
        file_hash = generate_file_hash(local_xlsx_file)

        # Check if the file already exists in the database
        if S3File.objects.filter(file_hash=file_hash).exists():
            print(f"File {latest_file_name} already processed. Skipping.")
            os.remove(local_xlsx_file)  # Clean up the local XLSX file
            continue

        # Convert the xlsx file to csv
        xlsx_to_csv(local_xlsx_file, local_csv_file)

        # Save the file metadata to the database
        S3File.objects.create(name=latest_file_name, file_hash=file_hash)
        save_csv_to_db(local_csv_file)

        # Clean up local files
        os.remove(local_xlsx_file)
        os.remove(local_csv_file)


if __name__ == "__main__":
    main()
