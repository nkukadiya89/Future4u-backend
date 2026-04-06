import json
import time
import uuid

import requests
from decouple import config


class GovernmentDocVerification:
    _group_id: str = str(uuid.uuid4())

    _payload: dict = {"task_id": str(uuid.uuid4()), "group_id": _group_id, "data": {}}
    _headers: dict = {
        "api-key": config("GOVT_DOC_API_KEY", default=""),
        "account-id": config("GOVT_DOC_ACCOUNT_ID", default=""),
        "Content-Type": "application/json",
    }

    _url_list: dict = {
        "request_data_url": "https://eve.idfy.com/v3/tasks?request_id=",
        "udhyam": "https://eve.idfy.com/v3/tasks/async/verify_with_source/udyam_aadhaar",
        "gstn": (
            "https://eve.idfy.com/v3/tasks/async/verify_with_source/ind_gst_certificate"
        ),
        "pan1": "https://eve.idfy.com/v3/tasks/async/verify_with_source/ind_pan",
        "pan": "https://eve.idfy.com/v3/tasks/async/verify_with_source/ind_pan_plus",
    }

    # Udhyan Verification
    def verify_udhyam(self, uam_number: str) -> dict:
        URL = self._url_list["udhyam"]
        self._payload.update({"data": {"uam_number": uam_number}})

        try:
            response = requests.post(URL, headers=self._headers, json=self._payload)

            res = json.loads(response.content)
            request_id = res.get("request_id", None)
            time.sleep(3)
            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=self._headers)

                res = json.loads(response.content)
                status = res[0].get("status")
                while status != "completed":
                    time.sleep(3)
                    response = requests.get(URL, headers=dict(self._headers))
                    res = json.loads(response.content)
                    status = res[0].get("status")

                verified_data = res[0].get("result", {}).get("source_output")
                data = {}
                data["company_name"] = verified_data.get("general_details").get(
                    "enterprise_name", ""
                )
                data["major_activity"] = verified_data.get("general_details").get(
                    "major_activity", ""
                )
                data["block"] = verified_data.get("official_address").get("block", "")
                data["city"] = verified_data.get("official_address").get("city", "")
                data["district"] = verified_data.get("official_address").get(
                    "district", ""
                )
                data["email"] = verified_data.get("official_address").get("email", "")
                data["pin"] = verified_data.get("official_address").get("pin", "")
                data["state"] = verified_data.get("official_address").get("state", "")
                data["town"] = verified_data.get("official_address").get("town", "")
                return data
            else:
                return {"error": "Detail not found."}
        except Exception as E:
            return {"error": f"Verification failed {E}"}

    # GSTN Verification
    def verify_gst(self, gst_no: str) -> dict:
        URL = self._url_list["gstn"]
        self._payload.update({"data": {"gstin": gst_no, "filing_status": True}})

        try:
            response = requests.post(
                URL, headers=self._headers, json=dict(self._payload)
            )
            res = json.loads(response.content)
            request_id = res.get("request_id", None)
            time.sleep(3)
            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=dict(self._headers))

                res = json.loads(response.content)
                status = res[0].get("status")
                while status != "completed":
                    time.sleep(3)
                    response = requests.get(URL, headers=dict(self._headers))
                    res = json.loads(response.content)
                    status = res[0].get("status")

                verified_data = res[0].get("result", {}).get("source_output", {})
                data = {}
                if verified_data.get("gstin_status").lower() == "active":
                    data["company"] = verified_data.get("trade_name", "")
                    data["legal_name"] = verified_data.get("legal_name", "")
                    address = verified_data.get(
                        "principal_place_of_business_fields", {}
                    ).get("principal_place_of_business_address")
                    data["building_name"] = address.get("building_name", "")
                    data["floor_number"] = address.get("floor_number", "")
                    data["door_name"] = address.get("door_number")
                    data["city"] = address.get("location", "")
                    data["pincode"] = address.get("pincode", "")
                    data["street"] = address.get("street", "")
                    data["status"] = verified_data.get("gstin_status", "")
                    data["state"] = verified_data.get("state_jurisdiction_code", "")
                    data["business_activity"] = verified_data.get(
                        "nature_of_business_activity", ""
                    )
                else:
                    data["error"] = "GSTN Status is not active"
                return data
            else:
                return {"error": "Detail not Found"}
        except Exception as E:
            return {"error": f"Verification failed {E}"}

    # PAN Verification
    def verify_pan(self, pan_no: str, full_name: str, dob: str) -> dict:
        URL = self._url_list["pan"]

        self._payload.update({"data": {"id_number": pan_no}})

        try:
            response = requests.post(URL, headers=self._headers, json=self._payload)
            res = json.loads(response.content)
            request_id = res.get("request_id", None)
            time.sleep(3)
            if request_id:
                URL = f"{self._url_list['request_data_url']}{request_id}"
                response = requests.get(URL, headers=self._headers)

                res = json.loads(response.content)
                status = res[0].get("status")
                while status != "completed":
                    time.sleep(3)
                    response = requests.get(URL, headers=dict(self._headers))
                    res = json.loads(response.content)
                    status = res[0].get("status")

                verified_data = res[0].get("result", {}).get("source_output")
                data = {}
                data["category"] = verified_data.get("category", "")
                data["full_name"] = verified_data.get("full_name", "")
                data["dob"] = verified_data.get("dob", "")
                data["email"] = verified_data.get("email", "")
                data["status"] = verified_data.get("status", "")
                return data
            else:
                return {"error": "Detail not Found"}
        except Exception as E:
            return {"error": f"Verification failed {E}"}


def run():
    while True:
        option = int(input("What you want to verify: "))
        if option == 1:
            udhyam_no = input("Enter Udhyam Number: ")
            GovernmentDocVerification().verify_udhyam(udhyam_no)
        elif option == 2:
            gst_no = input("Enter GSTIN: ")
            GovernmentDocVerification().verify_gst(gst_no)
        elif option == 3:
            pan_no = input("Enter PAN: ")
            full_name = input("Enter Full Name")
            dob = input("Enter DOB")
            GovernmentDocVerification().verify_pan(pan_no, full_name, dob)
        elif option == 4:
            break
        else:
            continue


if __name__ == "__main__":
    run()
