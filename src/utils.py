import csv
import json
import logging
from pathlib import Path
from typing import Generator, Dict, Any

def write_bookings_tables(self, records: Generator[Dict[str, Any], None, None]):
    bookings = []
    booking_events = []
    booking_locations = []
    booking_status_changes = []
    bookings_updator = []
    bookings_creator = []
    bookings_owner = []

    addresses = {}
    phone_numbers = {}
    email_addresses = {}

    for raw_booking in records:
        booking_id = raw_booking.get("id")

        location = raw_booking.get("location")
        if location:
            location_id = location.get("id")
            booking_locations.append({
                "booking_id": booking_id,
                "location_id": location_id,
                "name": location.get("name"),
                "customer_id": location.get("customer_id"),
                "site_id": location.get("site_id")
            })

            for addr in location.get("addresses", []):
                addr_id = addr.get("id")
                if addr_id:
                    addresses[addr_id] = addr

            for phone in location.get("phone_numbers", []):
                phone_id = phone.get("id")
                if phone_id and phone.get("number"):
                    phone_numbers[phone_id] = {
                        "id": phone_id,
                        "number": phone.get("number"),
                        "phone_number_type": phone.get("phone_number_type"),
                        "extension": phone.get("extension")
                    }

        for change in raw_booking.get("status_changes", []):
            booking_status_changes.append(change | {"booking_id": booking_id})

        for eid in raw_booking.get("event_ids", []):
            booking_events.append({
                "booking_id": booking_id,
                "event_id": eid
            })

        for role, container in [
            ("updator", bookings_updator),
            ("creator", bookings_creator),
            ("owner", bookings_owner)
        ]:
            user = raw_booking.get(role)
            if user and isinstance(user, dict) and "id" in user:
                flat_user = {
                    k: v for k, v in user.items()
                    if k not in {"phone_numbers", "email_addresses"}
                }

                email_list = user.get("email_addresses")
                if isinstance(email_list, list) and len(email_list) > 0:
                    first_email = email_list[0]
                    if isinstance(first_email, dict):
                        flat_user["email"] = first_email.get("address")

                        email_id = first_email.get("id")
                        if email_id and first_email.get("address"):
                            email_addresses[email_id] = {
                                "id": email_id,
                                "address": first_email["address"]
                            }

                flat_user["booking_id"] = booking_id
                container.append(flat_user)

                for phone in user.get("phone_numbers", []):
                    phone_id = phone.get("id")
                    if phone_id and phone.get("number"):
                        phone_numbers[phone_id] = {
                            "id": phone_id,
                            "number": phone.get("number"),
                            "phone_number_type": phone.get("phone_number_type"),
                            "extension": phone.get("extension")
                        }

                for email in email_list or []:
                    email_id = email.get("id")
                    if email_id and email.get("address"):
                        email_addresses[email_id] = {
                            "id": email_id,
                            "address": email.get("address")
                        }

        contact = raw_booking.get("contact")
        if contact and isinstance(contact, dict):
            for email in contact.get("email_addresses", []):
                email_id = email.get("id")
                if email_id and email.get("address"):
                    email_addresses[email_id] = {
                        "id": email_id,
                        "address": email.get("address")
                    }

            for phone in contact.get("phone_numbers", []):
                phone_id = phone.get("id")
                if phone_id and phone.get("number"):
                    phone_numbers[phone_id] = {
                        "id": phone_id,
                        "number": phone.get("number"),
                        "phone_number_type": phone.get("phone_number_type"),
                        "extension": phone.get("extension")
                    }

        flat_booking = {
            k: v for k, v in raw_booking.items()
            if not isinstance(v, (dict, list)) and k not in {
                "owner", "creator", "updator", "contact", "account", "location"
            }
        }
        flat_booking["location_id"] = location.get("id") if location else None
        flat_booking["owner_id"] = (
            raw_booking.get("owner", {}).get("id") if isinstance(raw_booking.get("owner"), dict) else None
        )
        flat_booking["creator_id"] = (
             raw_booking.get("creator", {}).get("id") if isinstance(raw_booking.get("creator"), dict) else None
        )
        flat_booking["updator_id"] = (
            raw_booking.get("updator", {}).get("id") if isinstance(raw_booking.get("updator"), dict) else None
        )
        bookings.append(flat_booking)

    out = Path(self.configuration.data_dir) / "out" / "tables"
    out.mkdir(parents=True, exist_ok=True)

    def write_csv(name: str, rows: list[Dict[str, Any]], pk: list[str]):
        file_path = out / f"{name}.csv"
        if not rows:
            logging.info(f"No rows for {name}")
            return
        all_keys = sorted(set().union(*(row.keys() for row in rows)))
        with open(file_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            for row in rows:
                safe_row = {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in row.items()
                }
                writer.writerow(safe_row)
        self.write_manifest(self.create_out_table_definition(f"{name}.csv", primary_key=pk))

    write_csv("bookings", bookings, ["id"])
    write_csv("booking_events", booking_events, ["booking_id", "event_id"])
    write_csv("booking_locations", booking_locations, ["booking_id", "location_id"])
    write_csv("booking_status_changes", booking_status_changes, ["booking_id", "created_at", "status"])
    write_csv("bookings_updator", bookings_updator, ["booking_id"])
    write_csv("bookings_creator", bookings_creator, ["booking_id"])
    write_csv("bookings_owner", bookings_owner, ["booking_id"])
    write_csv("addresses", list(addresses.values()), ["id"])
    write_csv("phone_numbers", list(phone_numbers.values()), ["id"])
    write_csv("email_addresses", list(email_addresses.values()), ["id"])

    logging.info("All normalized booking tables written.")
