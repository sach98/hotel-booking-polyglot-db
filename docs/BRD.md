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
  $$\text{Invoice Amount} = \text{Duration (Nights)} \times \text{Nightly Room Rate}$$
- **Auditability Rule:** Invoices must reference a valid `BookingID` and store generated timestamps.

### BR-03: Polyglot Document Store (MongoDB Catalogue)
- **Use Case:** Hotel catalogue browse & search.
- **Document Model:** Flexible JSON schema holding hotel attributes, location tags, star ratings, and nested facility lists.
- **Fallback Rule:** Must support `mongomock` in-memory fallback for local automated testing when live MongoDB daemon is unavailable.

---

## 3. Data Dictionary & Entity Relationship (ER) Summary

| Entity | Primary Key | Foreign Keys | Key Attributes | Business Rule |
|---|---|---|---|---|
| `CUSTOMER` | `CustomerID` | None | Name, Contact, Age | Must be registered before booking. |
| `HOTEL` | `HotelID` | None | Name, Postcode, Parking_space | Master catalogue entity. |
| `ROOM` | `RoomID` | `HotelID` | Room_number, Type, Price_per_night | Nightly rate drives invoice calculation. |
| `BOOKING` | `BookingID` | `CustomerID`, `HotelID`, `RoomID` | Arrival_date, Checkout_date, Duration | Duration derived from checkout minus arrival. |
| `INVOICE` | `InvoiceID` | `BookingID` | Total_amount, Issue_date | Auto-calculated upon booking confirmation. |
| `FEEDBACK` | `FeedbackID` | `BookingID`, `CustomerID`, `HotelID` | Rating (1-5), Comments | Guest review linked to completed stay. |
