import csv
import json
import logging
from pathlib import Path
from typing import Generator, Dict, Any

def write_output_table(self, name: str, rows: list[Dict[str, Any]], primary_key: list[str]):
    """
    Generic CSV writer with manifest creation for Keboola tables.
    """
    out_dir = Path(self.configuration.data_dir) / "out" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"{name}.csv"

    if not rows:
        logging.info(f"No rows for {name}")
        return

    fieldnames = sorted({k for row in rows for k in row})
    with open(file_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for k, v in row.items()
            })

    self.write_manifest(self.create_out_table_definition(f"{name}.csv", primary_key=primary_key))

def write_leads_tables(self, records: Generator[Dict[str, Any], None, None]):
    leads = []
    lead_sources = []
    selected_lead_sources = []
    owners = []
    locations = []

    addresses = {}
    phone_numbers = {}

    for raw_lead in records:
        lead_id = raw_lead.get("id")

        # Lead source object (flatten ID into lead row)
        lead_source_obj = raw_lead.get("lead_source")
        lead_source_id = lead_source_obj.get("id") if isinstance(lead_source_obj, dict) else None

        # Flatten the main lead fields
        flat_lead = {
            k: v for k, v in raw_lead.items()
            if not isinstance(v, (dict, list)) and k not in {
                "owner", "location", "lead_source", "lead_sources", "selected_lead_sources"
            }
        }
        flat_lead["owner_id"] = raw_lead.get("owner", {}).get("id") if isinstance(raw_lead.get("owner"), dict) else None
        flat_lead["location_id"] = (
            raw_lead.get("location", {}).get("id") if isinstance(raw_lead.get("location"), dict) else None
        )
        flat_lead["lead_source_id"] = lead_source_id
        leads.append(flat_lead)

        owner = raw_lead.get("owner")
        if owner and isinstance(owner, dict) and "id" in owner:
            owner["lead_id"] = lead_id
            owners.append(owner)

        # Lead Sources
        for source in raw_lead.get("lead_sources", []):
            if source.get("id"):
                lead_sources.append({
                    "lead_id": lead_id,
                    "lead_source_id": source["id"],
                    "lead_source_name": source.get("name")
                })

        # Selected Lead Sources
        for selected in raw_lead.get("selected_lead_sources", []):
            selected["lead_id"] = lead_id
            selected_lead_sources.append(selected)

        location = raw_lead.get("location")
        if location and isinstance(location, dict):
            loc_id = location.get("id")
            locations.append({
                "lead_id": lead_id,
                "location_id": loc_id,
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

    write_output_table(self,"leads", leads, ["id"])
    write_output_table(self,"lead_sources", lead_sources, ["lead_id", "lead_source_id"])
    write_output_table(self,"selected_lead_sources", selected_lead_sources, ["lead_id", "lead_source_id"])
    write_output_table(self,"owners", owners, ["lead_id"])
    write_output_table(self,"locations", locations, ["lead_id", "location_id"])
    write_output_table(self,"addresses", list(addresses.values()), ["id"])
    write_output_table(self,"phone_numbers", list(phone_numbers.values()), ["id"])

    logging.info("All normalized leads tables written.")

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

    write_output_table(self, "bookings", bookings, ["id"])
    write_output_table(self, "booking_events", booking_events, ["booking_id", "event_id"])
    write_output_table(self, "booking_locations", booking_locations, ["booking_id", "location_id"])
    write_output_table(self, "booking_status_changes", booking_status_changes, ["booking_id", "created_at", "status"])
    write_output_table(self, "bookings_updator", bookings_updator, ["booking_id"])
    write_output_table(self, "bookings_creator", bookings_creator, ["booking_id"])
    write_output_table(self, "bookings_owner", bookings_owner, ["booking_id"])
    write_output_table(self, "addresses", list(addresses.values()), ["id"])
    write_output_table(self, "phone_numbers", list(phone_numbers.values()), ["id"])
    write_output_table(self, "email_addresses", list(email_addresses.values()), ["id"])

    logging.info("All normalized booking tables written.")
