from datetime import datetime, UTC
import logging

from keboola.component.base import ComponentBase
from keboola.component.exceptions import UserException
from configuration import Configuration
from api_client import APIClient
from utils import write_bookings_tables, write_leads_tables


class Component(ComponentBase):
    def __init__(self):
        super().__init__()

    def run(self):
        run_time = datetime.now(UTC)
        run_time_str = run_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        config = Configuration(**self.configuration.parameters)
        state = self.get_state_file()
        api_client = APIClient(config, state)
        new_state = {}

        if config.endpoints.bookings:
            logging.info("Fetching bookings data...")
            write_bookings_tables(self, api_client.get_bookings())

        if config.endpoints.leads:
            logging.info("Fetching leads data...")
            write_leads_tables(self, api_client.get_leads())

        new_state["last_successful_run"] = run_time_str
        self.write_state_file(new_state)
        logging.info("Component finished successfully.")

"""
        Main entrypoint
"""
if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
