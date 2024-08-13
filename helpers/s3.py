from datetime import datetime, timedelta
import boto3


class S3Service:
    def __init__(self, s3="s3", region_name=None, aws_access_key_id=None, aws_secret_access_key=None) -> None:
        self.s3 = boto3.resource(
            service_name=s3,
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

    def download_from_s3(self, s3_file, s3_bucket, local_file):
        try:
            self.s3.Bucket(s3_bucket).download_file(s3_file, local_file)
            return True
        except Exception as e:
            raise Exception(
                f"Failed to download {s3_file} from {s3_bucket}: {e}")

    def get_previous_day_files(self, s3_bucket):
        try:
            bucket = self.s3.Bucket(s3_bucket)
            # Filter out folders (objects whose keys end with '/') and files that do not end with .xlsx
            files = [obj for obj in bucket.objects.all()
                    if not obj.key.endswith('/') and obj.key.endswith('.xlsx')]

            # Get the current date and the date for the previous day
            current_date = datetime.now().date()
            previous_day = current_date - timedelta(days=1)

            # Filter files to include only those from the previous day
            previous_day_files = [
                obj for obj in files
                if obj.last_modified.date() == previous_day
            ]

            if not previous_day_files:
                raise Exception(
                    f"No files from the previous day found in {s3_bucket}")

            return [file.key for file in previous_day_files]

        except Exception as e:
            raise Exception(
                f"Failed to get the previous day files from {s3_bucket}: {e}")
