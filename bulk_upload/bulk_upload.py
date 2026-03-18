import csv
import io
import sys

from django.db import IntegrityError, transaction
from rest_framework import status

from pincode.models import PinCode
from user.models import User


class Pincode_BulkUpload:
    __file_to_process = None

    def __init__(self, upload_file) -> None:
        self.__file_to_process = upload_file

    def process_pincode_csv(self, created_by):
        response = {}

        if self.__file_to_process.content_type != "text/csv":  # type: ignore
            response["data"] = "File type not allowed"
            response["status"] = False
            return response

        if sys.platform == "win32":
            file_data = self.__file_to_process.read().decode("cp1252")  # type: ignore
        else:
            file_data = self.__file_to_process.read().decode("utf-8")

        reader = csv.DictReader(io.StringIO(file_data))

        user = User.objects.get(id=created_by)

        try:
            with transaction.atomic():
                for row in reader:
                    pincode_number = row.get("pincode_number")

                    existing_pincode = PinCode.objects.filter(
                        pincode_number=pincode_number
                    ).first()
                    if not existing_pincode:
                        PinCode.objects.create(
                            pincode_number=pincode_number, created_by=user
                        )

                response["success"] = True
                response["message"] = "Pincode Bulk uploaded and processed successfully"
                response["status"] = status.HTTP_200_OK
                return response

        except IntegrityError as e:
            response["success"] = False
            response["message"] = str(e)
            response["status"] = status.HTTP_400_BAD_REQUEST
            return response
