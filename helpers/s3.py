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

    def get_latest_file(self, s3_bucket):
        try:
            bucket = self.s3.Bucket(s3_bucket)
            # Filter out folders (objects whose keys end with '/')
            files = [obj for obj in bucket.objects.all()
                     if not obj.key.endswith('/')]
            latest_file = max(files, key=lambda x: x.last_modified)
            return latest_file.key
        except Exception as e:
            raise Exception(
                f"Failed to get the latest file from {s3_bucket}: {e}")
