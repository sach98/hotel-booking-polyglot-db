"""
Interactive console CRUD menu for the MAGS hotel-booking platform.

This is the menu-driven admin tool that originally lived as a ``while True /
input()`` loop inside the notebook. It is kept here as a standalone script so
the notebook can run top-to-bottom without blocking on user input.

Run it after building the database:

    sqlite3 data/hotel.db < sql/seed.sql
    python app.py

All writes go through the parameterised helpers in ``db.py``.
"""

from __future__ import annotations

import sys

import db

# Column type hints used to validate console input before it reaches the DB.
# (Validation is best-effort UX; safety comes from parameterised queries.)
COLUMN_TYPES: dict[str, dict[str, str]] = {
    "Customer": {
        "CustomerID": "int", "First_name": "str", "Last_name": "str",
        "Address": "str", "Postal_code": "str", "Contact_number": "str",
        "Age": "int",
    },
    "Booking": {
        "BookingID": "int", "Arrival_date": "date", "Checkout_date": "date",
        "Cancellation": "bool", "Duration": "int", "Number_of_guests": "int",
        "Meal": "bool", "CustomerCustomerID": "int", "HotelHotelID": "int",
    },
    "Hotel": {
        "HotelID": "int", "Contact": "str", "Name": "str", "Address": "str",
        "Postal_code": "str", "Parking_space": "bool",
    },
    "Invoice": {
        "InvoiceID": "int", "BookingBookingID": "int", "Amount": "int",
        "Discount": "int", "Date": "date", "Time": "str",
    },
    "Room": {
        "Room_number": "int", "Room_type": "str", "Price": "int",
        "HotelHotelID": "int", "BookingBookingID": "int",
    },
    "Feedback": {
        "FeedbackID": "int", "BookingBookingID": "int", "Feedback_text": "str",
        "Rating": "int", "HotelHotelID": "int",
    },
}

import datetime


def coerce(raw: str, type_decl: str):
    """Validate/convert a raw input string to its declared type or raise."""
    raw = raw.strip()
    if type_decl == "str":
        return raw
    if type_decl == "int":
        return int(raw)  # raises ValueError on bad input
    if type_decl == "bool":
        if raw in ("0", "1"):
            return int(raw)
        if raw.lower() in ("true", "false"):
            return 1 if raw.lower() == "true" else 0
        raise ValueError("expected 0/1 or true/false")
    if type_decl == "date":
        datetime.datetime.strptime(raw, "%Y-%m-%d")  # validate format
        return raw
    return raw


def ask_table() -> str:
    name = input("\nTable name: ").strip().title()
    if name not in db.SCHEMA:
        raise ValueError("That table does not exist.")
    return name


def ask_existing_pk(conn, table: str):
    """Prompt for a primary-key value that already exists in the table."""
    pk_col = db.SCHEMA[table][0]
    existing = {str(v) for v in db.get_unique(conn, table, pk_col)}
    value = input(f"Provide the {pk_col}: ").strip()
    if value not in existing:
        raise ValueError("That id does not exist.")
    return pk_col, value


def do_create(conn) -> None:
    table = ask_table()
    types = COLUMN_TYPES[table]
    cols = db.SCHEMA[table]
    pk_col = cols[0]

    values = [db.next_id(conn, table, pk_col)]  # auto-generate the primary key
    print(f"(auto {pk_col} = {values[0]})")

    for col in cols[1:]:
        while True:
            try:
                values.append(coerce(input(f"  {col}: "), types[col]))
                break
            except ValueError as exc:
                print(f"  invalid ({exc}); try again.")

    db.insert_row(conn, table, values)
    print("Row created.")


def do_edit(conn) -> None:
    table = ask_table()
    pk_col, pk_value = ask_existing_pk(conn, table)
    print(db.get_row(conn, table, pk_col, pk_value).to_string(index=False))

    set_col = input("Column to edit: ").strip()
    if set_col not in db.SCHEMA[table]:
        raise ValueError("No such column.")
    new_value = coerce(input("New value: "), COLUMN_TYPES[table][set_col])
    db.update_value(conn, table, pk_col, pk_value, set_col, new_value)
    print("Updated.")


def do_invoice(conn) -> None:
    book_id = input("\nBooking id: ").strip()
    existing = {str(v) for v in db.get_unique(conn, "Invoice", "BookingBookingID")}
    if book_id not in existing:
        raise ValueError("No invoice for that booking.")
    print(db.get_row(conn, "Invoice", "BookingBookingID", book_id).to_string(index=False))


def do_delete_row(conn) -> None:
    table = ask_table()
    pk_col, pk_value = ask_existing_pk(conn, table)
    db.delete_row(conn, table, pk_col, pk_value)
    print("Deleted.")


def do_null_value(conn) -> None:
    table = ask_table()
    pk_col, pk_value = ask_existing_pk(conn, table)
    set_col = input("Attribute to set NULL: ").strip()
    if set_col not in db.SCHEMA[table]:
        raise ValueError("No such column.")
    db.null_value(conn, table, pk_col, pk_value, set_col)
    print("Cleared.")


def do_print_row(conn) -> None:
    table = ask_table()
    pk_col, pk_value = ask_existing_pk(conn, table)
    print(db.get_row(conn, table, pk_col, pk_value).to_string(index=False))


def do_print_table(conn) -> None:
    table = ask_table()
    print(db.get_table(conn, table).to_string(index=False))


def do_print_db(conn) -> None:
    for table in db.all_tables():
        print(f"\n=== {table} ===")
        print(db.get_table(conn, table).to_string(index=False))


MENU = """
What would you like to do?
  1. Create a new entry
  2. Edit an existing entry
  3. Retrieve an invoice for a booking
  4. Delete an entry by id
  5. Set a value to NULL for an id
  6. Print a single row
  7. Print an entire table
  8. Print the entire database
  9. Exit
> """

ACTIONS = {
    "1": do_create,
    "2": do_edit,
    "3": do_invoice,
    "4": do_delete_row,
    "5": do_null_value,
    "6": do_print_row,
    "7": do_print_table,
    "8": do_print_db,
}


def main() -> None:
    conn = db.connect()
    try:
        while True:
            choice = input(MENU).strip()
            if choice == "9":
                print("Goodbye!")
                return
            action = ACTIONS.get(choice)
            if action is None:
                print("Not a valid option; try again.")
                continue
            try:
                action(conn)
            except ValueError as exc:
                print(f"Action cancelled: {exc}")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
