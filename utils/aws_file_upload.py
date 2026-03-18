import os
from os import path, remove
from os.path import isfile
from urllib.parse import urlparse

import boto3
from decouple import config
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from PIL import Image
from rest_framework import serializers

ACCESS_KEY = config("AWS_ACCESS_KEY")
SECRET_KEY = config("AWS_SECRET_KEY")
REGION_NAME = config("REGION_NAME")
BUCKET = config("BUCKET_NAME")


def get_bucket_file_folder(aws_file_url):
    o = urlparse(aws_file_url, allow_fragments=False)
    return o.path.lstrip("/")


def file_extention(file_path):
    return path.splitext(file_path)[1]


def upload_file_to_bucket(
    upload_file, allowed_type, folder_name, p_value, file_name=None
):
    file_type = file_extention(str(upload_file))

    if file_type.lower() not in allowed_type:
        raise serializers.ValidationError("File Type not supported")

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    if file_name is None:
        file_name = timezone.now().strftime("%Y%m%d_%H%M%S")

    # File path for temporary storage
    tempfile = settings.MEDIA_ROOT + file_name + file_type

    # Handle image files
    if file_type.lower() in [".jpg", ".jpeg", ".png"]:
        file_to_upload = Image.open(upload_file)
        picture_format = "image/" + file_to_upload.format.lower()
        file_to_upload.save(tempfile)
    else:
        # For non-image files (e.g., PDFs), save directly
        with open(tempfile, "wb") as temp_file:
            for chunk in upload_file.chunks():
                temp_file.write(chunk)
        picture_format = "application/pdf"

    s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type

    # Validate file size (limit: 5MB)
    file_size = os.path.getsize(tempfile) / 1000
    if file_size > 5120:
        remove(tempfile)
        raise serializers.ValidationError("File size too large")

    # Upload to S3
    s3.upload_file(
        tempfile,
        BUCKET,
        s3_file,
        ExtraArgs={"ACL": "public-read", "ContentType": picture_format},
    )

    aws_file_url = f"http://{BUCKET}.s3.{REGION_NAME}.amazonaws.com/{s3_file}"
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": get_bucket_file_folder(aws_file_url)},
        ExpiresIn=300,
    )

    # Clean up temporary file
    if isfile(tempfile):
        remove(tempfile)
    return aws_file_url, presigned_url


def upload_doc_file(upload_file, allowed_type, folder_name, p_value, file_name=None):
    file_type = file_extention(str(upload_file))

    if file_type.lower() not in allowed_type:
        raise serializers.ValidationError("File Type not supported")

    if file_name is None:
        file_name = timezone.now().strftime("%Y%m%d-%H%M%S")

    path = default_storage.save(
        "./" + upload_file.name, ContentFile(upload_file.read())
    )
    tempfile = os.path.join(settings.MEDIA_ROOT, path)

    s3 = boto3.client(
        "s3",
        region_name=REGION_NAME,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    s3_file = f"{folder_name}" + str(p_value) + "_" + file_name + file_type

    aws_file_url = f"http://{BUCKET}.s3.{REGION_NAME}.amazonaws.com/{s3_file}"
    file_size = os.path.getsize(tempfile) / 1000
    if file_size > 5120:
        remove(tempfile)
        raise serializers.ValidationError("File size too large")

    s3.upload_file(
        tempfile,
        BUCKET,
        s3_file,
        ExtraArgs={"ACL": "public-read"},
    )
    if isfile(tempfile):
        remove(tempfile)

    return aws_file_url


def delete_uploaded_file(uploaded_file):
    if uploaded_file:
        s3 = boto3.client(
            "s3",
            region_name=REGION_NAME,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
        )
        file_to_delete = get_bucket_file_folder(uploaded_file)
        if s3.list_objects_v2(Bucket=BUCKET, Prefix=file_to_delete)["KeyCount"] >= 1:
            s3.delete_object(Bucket=BUCKET, Key=file_to_delete)
            return True
        else:
            return False
    else:
        return True
