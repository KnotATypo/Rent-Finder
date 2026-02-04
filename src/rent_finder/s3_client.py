import os
from typing import Dict

import boto3
import botocore


class S3Client:
    def __init__(self):
        s3 = boto3.resource(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_ACCESS_KEY"),
            aws_session_token=None,
            config=boto3.session.Config(signature_version="s3v4"),
            verify=False,
        )
        self.bucket = s3.Bucket("rent-finder")

    def put_objects(self, objects: Dict[str, str]) -> None:
        for key, body in objects.items():
            self.bucket.put_object(Key=key, Body=body)

    def object_exists(self, object_name: str) -> bool:
        try:
            self.bucket.Object(object_name).load()
            return True
        except botocore.exceptions.ClientError:
            return False

    def get_object(self, object_name: str) -> bytes:
        resp = self.bucket.Object(object_name).get()
        content = resp["Body"].read()
        # Ensure the string content is decoded from bytes
        if "blurb.html" in object_name:
            content = content.decode("utf-8")
        return content

    def get_image_names(self, listing_id: str):
        resp = self.bucket.meta.client.list_objects_v2(Bucket=self.bucket.name, Prefix=f"{listing_id}/")
        files = [os.path.basename(x["Key"]) for x in resp["Contents"]]
        return [file for file in files if file != "blurb.html"]
