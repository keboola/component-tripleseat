import logging
import requests
from typing import Dict, Generator, Any

from configuration import Configuration

API_BASE_URL = "https://api.tripleseat.com"
TOKEN_URL = f"{API_BASE_URL}/oauth/token"


class APIClient:
    def __init__(self, config: Configuration, state: Dict[str, str]):
        self.config = config
        self.state = state
        self.access_token = self._authenticate()

    def _authenticate(self) -> str:
        payload = {
            "client_id": self.config.authorization.client_id,
            "client_secret": self.config.authorization.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}

        logging.info("Requesting access token from Tripleseat...")
        response = requests.post(TOKEN_URL, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Failed to retrieve access token.")
        logging.info("Access token retrieved successfully.")
        return token

    def get_bookings(self) -> Generator[Dict[str, Any], None, None]:
        """
        Streams bookings using pagination and date filtering.
        Each booking is yielded as-is.
        """
        start_date = self.config.sync_options.resolved_date_from(self.state).strftime("%m/%d/%Y")
        end_date = (
            self.config.sync_options.resolved_date_to().strftime("%m/%d/%Y")
            if self.config.sync_options.date_to else None
        )

        headers = {"Authorization": f"Bearer {self.access_token}"}
        page = 1

        while True:
            params = {
                "page": page,
                "booking_updated_start_date": start_date
            }
            if end_date:
                params["booking_updated_end_date"] = end_date

            url = f"{API_BASE_URL}/v1/bookings.json"
            logging.debug(f"Fetching bookings page={page}, start={start_date}, end={end_date or 'N/A'}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            total_pages = data.get("total_pages", 0)

            if not results:
                logging.info(f"No more results on page {page}. Stopping.")
                break

            for record in results:
                yield record

            page += 1
            if page > total_pages:
                break

    def get_leads(self) -> Generator[Dict[str, Any], None, None]:
        """
        Streams leads using pagination and created_after date filtering.
        Each lead is yielded as-is.
        """
        created_after = self.config.sync_options.resolved_date_from(self.state).strftime("%m/%d/%Y")
        created_before = (
            self.config.sync_options.resolved_date_to().strftime("%m/%d/%Y")
            if self.config.sync_options.date_to
            else None
        )

        headers = {"Authorization": f"Bearer {self.access_token}"}
        page = 1

        while True:
            params = {"page": page, "created_after": created_after}

            url = f"{API_BASE_URL}/v1/leads.json"
            logging.debug(f"Fetching leads page={page}, created_after={created_after}, created_before={created_before}")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])
            total_pages = data.get("total_pages", 0)

            if not results:
                logging.info(f"No more results on page {page}. Stopping.")
                break

            for record in results:
                yield record

            page += 1
            if total_pages and page > total_pages:
                break
