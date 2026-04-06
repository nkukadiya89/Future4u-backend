import requests
from decouple import config


class GovernmentDocVerification:
    _headers: dict = {
        "Authorization": f"Bearer {config('BULKPE_API_KEY', default='')}",
        "Content-Type": "application/json",
    }

    _url_list: dict = {
        "gstn": "https://api.bulkpe.in/client/verifyGstin",
        "pan": "https://api.bulkpe.in/client/verifyPan",
        "pan_lite": "https://api.bulkpe.in/client/verifyPanLite",
    }

    # GSTN Verification
    def verify_gst(self, gst_no: str) -> dict:
        URL = self._url_list["gstn"]
        payload = {"gstin": gst_no}

        try:
            response = requests.post(URL, headers=self._headers, json=payload)
            res = response.json()

            if res.get("status") and res.get("statusCode") == 200:
                data = res.get("data", {})
                return {
                    "company": data.get("business_name", ""),
                    "legal_name": data.get("legal_name", ""),
                    "building_name": data.get("address_details", {}).get(
                        "building_name", ""
                    ),
                    "floor_number": data.get("address_details", {}).get(
                        "floor_number", ""
                    ),
                    "door_name": data.get("address_details", {}).get("door_number", ""),
                    "city": data.get("address_details", {}).get("city", ""),
                    "pincode": data.get("address_details", {}).get("pincode", ""),
                    "street": data.get("address_details", {}).get("street", ""),
                    "status": data.get("gstin_status", ""),
                    "state": data.get("center_jurisdiction", ""),
                    "business_activity": data.get("nature_of_business_activity", ""),
                }
            else:
                return {"error": "GST verification failed"}
        except Exception as E:
            return {"error": f"Verification failed {E}"}

    # PAN Verification
    def verify_pan(self, pan_no: str, full_name: str = None, dob: str = None) -> dict:
        # Use PAN Premium if DOB is provided, otherwise use PAN Lite
        URL = self._url_list["pan"] if dob else self._url_list["pan_lite"]

        if dob:
            payload = {"pan": pan_no, "dob": dob}
        else:
            payload = {"pan": pan_no}

        try:
            response = requests.post(URL, headers=self._headers, json=payload)
            res = response.json()

            if res.get("status") and res.get("statusCode") == 200:
                data = res.get("data", {})
                return {
                    "category": data.get("category", ""),
                    "full_name": data.get("name", ""),
                    "dob": data.get("date_of_birth", ""),
                    "email": data.get("email", ""),
                    "status": data.get("status", ""),
                }
            else:
                return {"error": "PAN verification failed"}
        except Exception as E:
            return {"error": f"Verification failed {E}"}


def run():
    while True:
        option = int(input("What you want to verify: "))
        if option == 1:
            gst_no = input("Enter GSTIN: ")
            GovernmentDocVerification().verify_gst(gst_no)
        elif option == 2:
            pan_no = input("Enter PAN: ")
            dob = input("Enter DOB (optional): ")
            full_name = input("Enter Full Name (optional): ")
            GovernmentDocVerification().verify_pan(pan_no, full_name, dob)
        elif option == 3:
            break
        else:
            continue


if __name__ == "__main__":
    run()
