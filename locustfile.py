import os

from locust import HttpUser, between, task


class APIUser(HttpUser):
    wait_time = between(1, 3)
    token = os.getenv("LOAD_TEST_BEARER_TOKEN", "")

    def on_start(self):
        if self.token:
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(3)
    def company_list(self):
        self.client.get("/api/v1/company/")

    @task(1)
    def company_detail(self):
        company_id = os.getenv("LOAD_TEST_COMPANY_ID", "1")
        self.client.get(f"/api/v1/company/{company_id}/")
