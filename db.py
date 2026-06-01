"""
Shared SQLite data-access helpers for the MAGS hotel-booking platform.

This module centralises the relational CRUD logic so that both the analysis
notebook and the interactive console app (``app.py``) use one implementation.

Design notes
------------
* Table and column *names* cannot be passed as SQL bind parameters, so they are
  validated against a fixed allow-list (``SCHEMA``) before being interpolated.
  This keeps identifier handling safe without a query builder dependency.
* All user-supplied *values* are passed as ``?`` placeholders (parameterised
  queries), which is the correct defence against SQL injection.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Iterable, Sequence

import pandas as pd

# Default location of the SQLite file, relative to the project root.
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "hotel.db")

# Single source of truth for the schema: table -> ordered column list.
# Used both to validate identifiers and to label result frames.
SCHEMA: dict[str, list[str]] = {
    "Customer": [
        "CustomerID", "First_name", "Last_name", "Address",
        "Postal_code", "Contact_number", "Age",
    ],
    "Booking": [
        "BookingID", "Arrival_date", "Checkout_date", "Cancellation",
        "Duration", "Number_of_guests", "Meal",
        "CustomerCustomerID", "HotelHotelID",
    ],
    "Hotel": [
        "HotelID", "Name", "Contact", "Address", "Postal_code", "Parking_space",
    ],
    "Invoice": [
        "InvoiceID", "BookingBookingID", "Amount", "Discount", "Date", "Time",
    ],
    "Room": [
        "Room_number", "Room_type", "Price", "HotelHotelID", "BookingBookingID",
    ],
    "Feedback": [
        "FeedbackID", "BookingBookingID", "Feedback_text", "Rating", "HotelHotelID",
    ],
}


def connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key enforcement enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# --- identifier validation -------------------------------------------------

def _check_table(table: str) -> str:
    if table not in SCHEMA:
        raise ValueError(f"Unknown table: {table!r}")
    return table


def _check_column(table: str, column: str) -> str:
    if column not in SCHEMA[_check_table(table)]:
        raise ValueError(f"Unknown column {column!r} for table {table!r}")
    return column


# --- create / read / update / delete ---------------------------------------

def insert_row(conn: sqlite3.Connection, table: str, values: Sequence) -> None:
    """Insert a full row. ``values`` must match the column order in ``SCHEMA``."""
    cols = SCHEMA[_check_table(table)]
    if len(values) != len(cols):
        raise ValueError(
            f"{table} expects {len(cols)} values, got {len(values)}"
        )
    placeholders = ", ".join("?" for _ in cols)
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    conn.execute(sql, tuple(values))   # parameterised: values are bound, not concatenated
    conn.commit()


def update_value(
    conn: sqlite3.Connection,
    table: str,
    pk_col: str,
    pk_value,
    set_col: str,
    new_value,
) -> None:
    """Set a single column for the row identified by ``pk_col = pk_value``."""
    _check_column(table, pk_col)
    _check_column(table, set_col)
    sql = f"UPDATE {table} SET {set_col} = ? WHERE {pk_col} = ?"
    conn.execute(sql, (new_value, pk_value))
    conn.commit()


def null_value(
    conn: sqlite3.Connection, table: str, pk_col: str, pk_value, set_col: str
) -> None:
    """Blank a single column (set NULL) for one row."""
    _check_column(table, pk_col)
    _check_column(table, set_col)
    sql = f"UPDATE {table} SET {set_col} = NULL WHERE {pk_col} = ?"
    conn.execute(sql, (pk_value,))
    conn.commit()


def delete_row(
    conn: sqlite3.Connection, table: str, pk_col: str, pk_value
) -> None:
    """Delete the row identified by ``pk_col = pk_value``."""
    _check_column(table, pk_col)
    sql = f"DELETE FROM {table} WHERE {pk_col} = ?"
    conn.execute(sql, (pk_value,))
    conn.commit()


def get_row(
    conn: sqlite3.Connection, table: str, pk_col: str, pk_value
) -> pd.DataFrame:
    """Return one row as a DataFrame."""
    _check_column(table, pk_col)
    sql = f"SELECT * FROM {table} WHERE {pk_col} = ?"
    return pd.read_sql_query(sql, conn, params=(pk_value,))


def get_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    """Return an entire table as a DataFrame."""
    _check_table(table)
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)


def get_unique(conn: sqlite3.Connection, table: str, column: str) -> list:
    """Return the distinct values of one column (e.g. existing primary keys)."""
    _check_column(table, column)
    sql = f"SELECT DISTINCT {column} FROM {table}"
    return [row[0] for row in conn.execute(sql).fetchall()]


def next_id(conn: sqlite3.Connection, table: str, pk_col: str) -> int:
    """Return max(pk) + 1, or 1 for an empty table."""
    _check_column(table, pk_col)
    row = conn.execute(f"SELECT MAX({pk_col}) FROM {table}").fetchone()
    return (row[0] or 0) + 1


def all_tables() -> Iterable[str]:
    return SCHEMA.keys()
