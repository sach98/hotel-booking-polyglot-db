# Business Requirements Document (BRD) & System Architecture Spec
## Hotel Booking Platform & Data Engine (Polyglot Persistence)

**Document Control**
- **Author:** Sachin Sharma (Lead Business Analyst)
- **Status:** Approved / Baseline
- **Target Audience:** Engineering Leads, Database Architects, Business Analytics Managers

---

## 1. Business Objective
An online travel and hospitality platform requires a backend data architecture that supports two competing workloads:
1. **High-Integrity Transactional Core (Bookings & Invoicing):** Requires strict ACID compliance, foreign key constraints, and financial calculation accuracy (zero orphaned records, automated billing).
2. **High-Throughput Catalogue Search:** Requires flexible, schema-less reads for hotel amenities, room rates, and guest reviews.

This project implements a **Polyglot Persistence Architecture** using SQLite (3NF normalized relational core) alongside MongoDB (document store for directory catalogue).

---

## 2. Business Requirements & System Specifications

### BR-01: Normalized Relational Core (3NF SQLite Schema)
- **Table Structure:** 6 normalized entities: `CUSTOMER`, `HOTEL`, `ROOM`, `BOOKING`, `INVOICE`, `FEEDBACK`.
- **Integrity Rule:** Primary Key (PK) and Foreign Key (FK) constraints strictly enforced ON (`PRAGMA foreign_keys = ON`).
- **Data Quality Rule:** 0 orphaned records during database generation and seeding.

### BR-02: Automated Invoicing & Billing Rules
- **Billing Logic:** Every confirmed booking must automatically calculate invoice total:
  $$\text{Invoice Amount} = \text{Duration (Nights)} \times \sum_{\text{rooms on the booking}} \text{Nightly Room Rate}$$
  The sum is required, not cosmetic. A booking may hold more than one room, so a
  per-booking total that reads a single room rate under-bills every multi-room
  stay. A booking holding no rooms bills 0, not NULL.
- **Auditability Rule:** Invoices must reference a valid `BookingID` and store generated timestamps.

### BR-04: Data Integrity Constraints Enforced In The Schema
These rules are enforced by the database, not by application code, so they hold
regardless of which client writes the row.
- **Chronology Rule:** `Checkout_date` must be strictly later than `Arrival_date`
  (`CHECK`). A stay cannot end before it begins, and a derived `Duration` must
  never be zero or negative.
- **Billing Cardinality Rule:** at most one invoice per booking (`UNIQUE` on
  `Invoice.BookingBookingID`).
- **Review Cardinality Rule:** at most one review per booking (`UNIQUE` on
  `Feedback.BookingBookingID`). A review with no booking reference is
  unattributed rather than duplicate, so NULL may repeat.

### BR-03: Polyglot Document Store (MongoDB Catalogue)
- **Use Case:** Hotel catalogue browse & search.
- **Document Model:** Flexible JSON schema holding hotel attributes, location tags, star ratings, and nested facility lists.
- **Fallback Rule:** Must support `mongomock` in-memory fallback for local automated testing when live MongoDB daemon is unavailable.

---

## 3. Data Dictionary & Entity Relationship (ER) Summary

Column names below are the delivered ones, verbatim from `sql/seed.sql`. They can
be re-checked against a built database with `PRAGMA table_info(<entity>)` and
`PRAGMA foreign_key_list(<entity>)`; `tests/test_hotel_db.py` asserts that the
allow-list in `db.py` still matches the shipped tables column for column.

| Entity | Primary Key | Foreign Keys | Key Attributes | Business Rule |
|---|---|---|---|---|
| `CUSTOMER` | `CustomerID` | None | First_name, Last_name, Contact_number, Age | Must be registered before booking. |
| `HOTEL` | `HotelID` | None | Name, Postal_code, Parking_space | Master catalogue entity. |
| `ROOM` | `Room_number` | `HotelHotelID`, `BookingBookingID` | Room_type, Price (per night) | Nightly rate drives invoice calculation. A room may be unassigned (`BookingBookingID` NULL). |
| `BOOKING` | `BookingID` | `CustomerCustomerID`, `HotelHotelID` | Arrival_date, Checkout_date, Duration, Cancellation | Duration derived from checkout minus arrival. Rooms attach to the booking, not the reverse. |
| `INVOICE` | `InvoiceID` | `BookingBookingID` (UNIQUE) | Amount, Discount, Date, Time | Auto-calculated upon booking confirmation. One per booking. |
| `FEEDBACK` | `FeedbackID` | `BookingBookingID` (UNIQUE), `HotelHotelID` | Rating (1-5), Feedback_text | Guest review linked to a completed stay. One per booking. |

**Room-to-booking direction.** The link between a stay and its rooms lives on
`ROOM.BookingBookingID`, so one booking can hold many rooms. `BOOKING` carries no
room key. This is what makes the aggregate in BR-02 necessary.

**Reconciliation note.** An earlier revision of this table contradicted the
delivered schema on three entities and has been corrected against it:
`ROOM` was documented with a `RoomID` primary key (it is `Room_number`) and
without its `BookingBookingID` foreign key; `BOOKING` was documented with a
`RoomID` foreign key that does not exist in the schema; and `FEEDBACK` was
documented with a `CustomerID` foreign key that does not exist either (guest
identity reaches feedback through the booking). The `INVOICE` attribute labels
`Total_amount` and `Issue_date` were also corrected to the delivered `Amount`
and `Date`/`Time`, and `Discount` was added.
