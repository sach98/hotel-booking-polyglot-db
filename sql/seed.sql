-- =============================================================================
-- MAGS Hotel Booking Platform - Relational seed script (SQLite)
-- -----------------------------------------------------------------------------
-- Builds the `hotel.db` SQLite database from scratch: 6-table 3NF schema plus
-- a synthetic sample dataset, so the project is fully reproducible with
-- no manual data entry.
--
--   Usage:  sqlite3 data/hotel.db < sql/seed.sql
--
-- All data below is fictional and generated for demonstration only.
-- Foreign keys are enabled so the sample rows are guaranteed referentially valid.
--
-- The dataset is in two parts:
--   1. Ten hand-written rows per table, kept readable for inspection.
--   2. A generated block (240 further customers and bookings) so the analytics
--      have enough volume to say something. Every generated value is a pure
--      arithmetic function of the row number, so re-running this script always
--      produces exactly the same database. See "Generated sample data" below.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- Idempotent: drop in dependency order so the script can be re-run cleanly.
DROP TABLE IF EXISTS Feedback;
DROP TABLE IF EXISTS Invoice;
DROP TABLE IF EXISTS Room;
DROP TABLE IF EXISTS Booking;
DROP TABLE IF EXISTS Customer;
DROP TABLE IF EXISTS Hotel;

-- -----------------------------------------------------------------------------
-- Schema (3NF). Parent tables first so child FKs resolve.
-- -----------------------------------------------------------------------------

CREATE TABLE Hotel (
    HotelID        INTEGER PRIMARY KEY,
    Name           TEXT    NOT NULL,
    Contact        TEXT,
    Address        TEXT,
    Postal_code    TEXT,
    Parking_space  INTEGER CHECK (Parking_space IN (0, 1))   -- boolean 0/1
);

CREATE TABLE Customer (
    CustomerID     INTEGER PRIMARY KEY,
    First_name     TEXT    NOT NULL,
    Last_name      TEXT    NOT NULL,
    Address        TEXT,
    Postal_code    TEXT,
    Contact_number TEXT,
    Age            INTEGER CHECK (Age >= 0)
);

CREATE TABLE Booking (
    BookingID          INTEGER PRIMARY KEY,
    Arrival_date       TEXT    NOT NULL,            -- ISO 8601 'YYYY-MM-DD'
    Checkout_date      TEXT    NOT NULL,
    Cancellation       INTEGER CHECK (Cancellation IN (0, 1)),
    Duration           INTEGER,                     -- derived: nights stayed
    Number_of_guests   INTEGER,
    Meal               INTEGER CHECK (Meal IN (0, 1)),
    CustomerCustomerID INTEGER NOT NULL,
    HotelHotelID       INTEGER NOT NULL,
    -- A stay must end after it starts. ISO 8601 text sorts chronologically, so
    -- a plain string comparison is a correct date comparison here. Without this
    -- the derived Duration can go negative and the invoice turns into a credit.
    CHECK (Checkout_date > Arrival_date),
    FOREIGN KEY (CustomerCustomerID) REFERENCES Customer (CustomerID),
    FOREIGN KEY (HotelHotelID)       REFERENCES Hotel    (HotelID)
);

CREATE TABLE Room (
    Room_number        INTEGER PRIMARY KEY,
    Room_type          TEXT,
    Price              INTEGER,                     -- price per night
    HotelHotelID       INTEGER NOT NULL,
    BookingBookingID   INTEGER,
    FOREIGN KEY (HotelHotelID)     REFERENCES Hotel   (HotelID),
    FOREIGN KEY (BookingBookingID) REFERENCES Booking (BookingID)
);

CREATE TABLE Invoice (
    InvoiceID        INTEGER PRIMARY KEY,
    -- One invoice per booking (the 1:1 cardinality the README documents).
    BookingBookingID INTEGER NOT NULL UNIQUE,
    Amount           INTEGER,                       -- derived: Duration * total nightly price
    Discount         INTEGER,
    Date             TEXT,
    Time             TEXT,
    FOREIGN KEY (BookingBookingID) REFERENCES Booking (BookingID)
);

CREATE TABLE Feedback (
    FeedbackID       INTEGER PRIMARY KEY,
    -- One review per booking. NULL is still allowed more than once, which is
    -- correct: an unattributed review is not a duplicate review.
    BookingBookingID INTEGER UNIQUE,
    Feedback_text    TEXT,
    Rating           INTEGER CHECK (Rating BETWEEN 1 AND 5),
    HotelHotelID     INTEGER NOT NULL,
    FOREIGN KEY (BookingBookingID) REFERENCES Booking (BookingID),
    FOREIGN KEY (HotelHotelID)     REFERENCES Hotel   (HotelID)
);

-- -----------------------------------------------------------------------------
-- Hand-written sample data (synthetic). Insert parents first, children after.
-- -----------------------------------------------------------------------------

INSERT INTO Hotel (HotelID, Name, Contact, Address, Postal_code, Parking_space) VALUES
    (4001, 'Crowne Plaza London Ealing',        '02082333200', 'Western Avenue, Ealing',        'W5 1HG',   0),
    (4002, 'Dorsett City London',               '02038051000', '9 Aldgate High Street',         'EC3N 1AH', 1),
    (4003, 'The Montana',                        '01803380449', '21 Belgrave Rd',                'Q2 5HU',   1),
    (4004, 'Sea Containers London',              '02037471000', '20 Upper Ground',               'SE1 9PD',  0),
    (4005, 'Grand Royale London Hyde Park',      '02073137900', '1-9 Inverness Terrace',         'W2 3JP',   1),
    (4006, 'Park Grand London Hyde Park',        '02072624521', '78-82 Westbourne Terrace',      'W2 6QA',   1),
    (4007, 'The 29 London',                      '02078340205', '29-31 St Georges Dr',           'SW1V 4DG', 0),
    (4008, 'Astor Court Hotel',                  '02076364133', '20 Hallam St',                  'W1W 6JQ',  1),
    (4009, 'New Linden Hotel',                   '02072214321', '59 Leinster Square',            'W2 4PS',   1),
    (4010, 'Hampton by Hilton London Waterloo',  '02074018080', '157 Waterloo Rd',               'SE1 8XA',  0);

INSERT INTO Customer (CustomerID, First_name, Last_name, Address, Postal_code, Contact_number, Age) VALUES
    (1001, 'Romali',   'Bottle',   '12 Maple Avenue',    'M1 4SD',   '9310129780', 69),
    (1002, 'Roshali',  'Tottle',   '48 Oak Lane',        'M2 9SD',   '8310129780', 89),
    (1003, 'Bomali',   'Rottle',   '5 Elm Close',        'M3 5SD',   '9310129770', 29),
    (1004, 'Simon',    'Williams', '17 High Street',     'L3 1SD',   '8989197919', 18),
    (1005, 'Michel',   'Cub',      '2 Market Street',    'L2 3SD',   '9129397802', 26),
    (1006, 'Christen', 'Hindu',    '9 Temple Road',      'CH2 7Y2',  '7210265809', 68),
    (1007, 'Mathew',   'Perry',    '221 Baker Street',   'BS2 1KY',  '7302897501', 55),
    (1008, 'Ricky',    'Ponting',  '10 Downing Street',  'DS2 1KT',  '7927896203', 77),
    (1009, 'Frank',    'Ribery',   '3 Berlin Street',    'BS2 2KY',  '8077762832', 40),
    (1010, 'Cheryl',   'Holman',   '7 Nashville Ave',    'TN3 7Z0',  '6155371731', 32);

-- Duration left NULL on insert; populated by the derivation step below.
INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation, Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID) VALUES
    (1000001, '2019-07-01', '2019-07-19', 0, NULL, 1, 1, 1001, 4001),
    (1000002, '2020-05-02', '2020-05-11', 0, NULL, 2, 0, 1002, 4002),
    (1000003, '2021-06-03', '2021-06-22', 0, NULL, 3, 1, 1003, 4003),
    (1000004, '2022-04-04', '2022-04-10', 0, NULL, 1, 1, 1004, 4004),
    (1000005, '2022-04-04', '2022-04-20', 1, NULL, 2, 1, 1005, 4005),
    (1000006, '2022-04-04', '2022-04-08', 0, NULL, 2, 0, 1006, 4006),
    (1000007, '2022-04-04', '2022-04-16', 0, NULL, 1, 1, 1007, 4007),
    (1000008, '2022-04-04', '2022-04-22', 0, NULL, 3, 1, 1008, 4008),
    (1000009, '2022-04-04', '2022-04-15', 0, NULL, 4, 1, 1009, 4009),
    (1000010, '2022-04-04', '2022-04-19', 1, NULL, 1, 1, 1010, 4010);

INSERT INTO Room (Room_number, Room_type, Price, HotelHotelID, BookingBookingID) VALUES
    (100, 'Single', 100, 4001, 1000001),
    (711, 'Double', 110, 4002, 1000002),
    (109, 'Double', 113, 4003, 1000003),
    (508, 'Triple', 225, 4004, 1000004),
    (103, 'Studio', 215, 4005, 1000005),
    (204, 'Studio', 250, 4006, 1000006),
    (305, 'Single', 105, 4007, 1000007),
    (506, 'Double', 112, 4008, 1000008),
    (707, 'Triple', 212, 4009, 1000009),
    (808, 'Studio', 260, 4010, 1000010);

INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time) VALUES
    (2001, 1000001, NULL, 60, '2019-07-19', '12:33'),
    (2002, 1000002, NULL, 33, '2020-05-11', '02:00'),
    (2003, 1000003, NULL, 20, '2021-06-22', '11:20'),
    (2004, 1000004, NULL, 29, '2022-04-10', '12:10'),
    (2005, 1000005, NULL, 34, '2022-04-20', '03:33'),
    (2006, 1000006, NULL, 23, '2022-04-08', '10:10'),
    (2007, 1000007, NULL, 19, '2022-04-16', '11:57'),
    (2008, 1000008, NULL, 13, '2022-04-22', '01:13'),
    (2009, 1000009, NULL, 24, '2022-04-15', '12:10'),
    (2010, 1000010, NULL, 19, '2022-04-19', '01:17');

INSERT INTO Feedback (FeedbackID, BookingBookingID, Feedback_text, Rating, HotelHotelID) VALUES
    (101, 1000001, 'Hotel room was very small, not recommended.', 2, 4001),
    (102, 1000002, 'Very nice and clean room, staff were friendly as well.', 5, 4002),
    (103, 1000003, 'Listing said the room sleeps 3 but the third bed was a sofa.', 1, 4003),
    (104, 1000004, 'Pretty decent; the integrated kitchen was a nice touch.', 4, 4004),
    (105, 1000005, 'Room had no ventilation at all.', 2, 4005),
    (106, 1000006, 'Cheap and cheerful, great for students.', 5, 4006),
    (107, 1000007, 'Room was alright but the staff were excellent.', 4, 4007),
    (108, 1000008, 'Room could have been bigger but no major complaints.', 3, 4008),
    (109, 1000009, 'Bathroom was small but a decent studio overall.', 4, 4009),
    (110, 1000010, 'The single room was barely big enough to walk in.', 1, 4010);

-- =============================================================================
-- Generated sample data (synthetic, deterministic)
-- -----------------------------------------------------------------------------
-- Ten rows per table is not enough to analyse: every hotel has exactly one
-- booking, so "bookings per hotel" is 1 everywhere and any average is a
-- single observation. This block adds 240 more customers and bookings
-- (250 bookings in total) so the analytics in `analysis.py` have something to
-- measure.
--
-- HOW THE VALUES ARE PRODUCED. There is no random number generator. Each row
-- number `n` is mixed into two 32-bit hashes (`h`, `h2`) by a quadratic
-- expression, and each field reads a different digit slice of one of them.
-- The mixing is what makes the fields look independent of one another; the
-- determinism is what makes the database reproducible byte for byte.
--
-- HONEST DISCLOSURE. `gen_hotel_params` below deliberately encodes a
-- relationship: hotels with a lower baseline rating are given a higher
-- cancellation rate. The analysis therefore recovers a pattern that was put
-- into the data on purpose. It demonstrates the analytical method on a dataset
-- with known structure. It is not a finding about real hotels.
-- =============================================================================

-- Per-hotel generator parameters.
--   rating_base  matches the hand-written review already seeded for that hotel.
--   cancel_pct   is set to 6 * (6 - rating_base): 30% at 1 star down to 6% at 5.
--   base_price   matches the hand-written room already seeded for that hotel.
CREATE TEMP TABLE gen_hotel_params (
    hid INTEGER PRIMARY KEY, base_price INTEGER, cancel_pct INTEGER, rating_base INTEGER
);
INSERT INTO gen_hotel_params (hid, base_price, cancel_pct, rating_base) VALUES
    (4001, 100, 24, 2),
    (4002, 110,  6, 5),
    (4003, 113, 30, 1),
    (4004, 225, 12, 4),
    (4005, 215, 24, 2),
    (4006, 250,  6, 5),
    (4007, 105, 12, 4),
    (4008, 112, 18, 3),
    (4009, 212, 12, 4),
    (4010, 260, 30, 1);

CREATE TEMP TABLE gen_first_name (i INTEGER PRIMARY KEY, name TEXT);
INSERT INTO gen_first_name (i, name) VALUES
    (0,'Amelia'),(1,'Noah'),(2,'Priya'),(3,'Jonas'),(4,'Chloe'),
    (5,'Marcus'),(6,'Aisha'),(7,'Tobias'),(8,'Elena'),(9,'Rohan'),
    (10,'Freya'),(11,'Samuel'),(12,'Nadia'),(13,'Oliver'),(14,'Leila'),
    (15,'Hugo'),(16,'Sofia'),(17,'Callum'),(18,'Mira'),(19,'Declan');

CREATE TEMP TABLE gen_last_name (i INTEGER PRIMARY KEY, name TEXT);
INSERT INTO gen_last_name (i, name) VALUES
    (0,'Hartley'),(1,'Okafor'),(2,'Lindqvist'),(3,'Ferreira'),(4,'Nakamura'),
    (5,'Brennan'),(6,'Kaur'),(7,'Moreau'),(8,'Vasquez'),(9,'Whitfield'),
    (10,'Adeyemi'),(11,'Sorensen'),(12,'Rahman'),(13,'Costa'),(14,'Delaney'),
    (15,'Novak'),(16,'Iyer'),(17,'Mbeki'),(18,'Larsen'),(19,'Quinn');

CREATE TEMP TABLE gen_room_type (i INTEGER PRIMARY KEY, name TEXT);
INSERT INTO gen_room_type (i, name) VALUES
    (0,'Single'),(1,'Double'),(2,'Triple'),(3,'Studio');

-- One row per generated record, carrying the two mixed hashes.
CREATE TEMP TABLE gen_row (n INTEGER PRIMARY KEY, h INTEGER, h2 INTEGER);
INSERT INTO gen_row (n, h, h2)
WITH RECURSIVE seq(n) AS (
    SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < 240
)
-- Each factor is reduced modulo a prime BEFORE multiplying. Without that the
-- product exceeds the 64-bit signed range, SQLite promotes it to a float, and
-- the low-order digits every field reads become rounding noise.
SELECT n,
       (((n * 2654435761 + 1013904223) % 1000003) * ((n * 40503    + 12345) % 999983)) % 4294967291,
       (((n * 1103515245 + 12345)      % 1000033) * ((n * 22695477 + 1)     % 999979)) % 4294967291
  FROM seq;

-- Customers 1011..1250.
INSERT INTO Customer (CustomerID, First_name, Last_name, Address, Postal_code, Contact_number, Age)
SELECT 1010 + g.n,
       f.name,
       l.name,
       (1 + (g.h2 / 7) % 250) || ' ' || CASE (g.h2 / 13) % 4
            WHEN 0 THEN 'Kingsway' WHEN 1 THEN 'Beech Grove'
            WHEN 2 THEN 'Carlisle Road' ELSE 'Priory Lane' END,
       'N' || (1 + (g.h / 3) % 9) || ' ' || (1 + (g.h / 19) % 9) || 'AB',
       '7' || printf('%09d', (g.h2 / 11) % 1000000000),
       18 + (g.h / 23) % 62
  FROM gen_row g
  JOIN gen_first_name f ON f.i = (g.h  / 7)   % 20
  JOIN gen_last_name  l ON l.i = (g.h2 / 137) % 20;

-- Bookings 1000011..1000250. Duration left NULL; derived below.
--   hotel        h  % 10          arrival    (h / 20000) % 730 days from 2023-01-01
--   nights       1 + (h / 1000) % 14         guests     1 + (h2 / 3) % 4
--   meal         (h2 / 11) % 2               customer   1001 + h2 % 250
--   cancelled    (h / 10) % 100 < cancel_pct for that hotel
INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation, Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
SELECT 1000010 + g.n,
       date('2023-01-01', '+' || ((g.h / 20000) % 730) || ' days'),
       date('2023-01-01', '+' || ((g.h / 20000) % 730 + 1 + (g.h / 1000) % 14) || ' days'),
       CASE WHEN (g.h / 10) % 100 < p.cancel_pct THEN 1 ELSE 0 END,
       NULL,
       1 + (g.h2 / 3) % 4,
       (g.h2 / 11) % 2,
       1001 + g.h2 % 250,
       p.hid
  FROM gen_row g
  JOIN gen_hotel_params p ON p.hid = 4001 + g.h % 10;

-- Primary room for every generated booking. Price jitters +/-20 around the
-- hotel's base rate.
INSERT INTO Room (Room_number, Room_type, Price, HotelHotelID, BookingBookingID)
SELECT 10000 + g.n,
       t.name,
       p.base_price - 20 + (g.h / 41) % 41,
       b.HotelHotelID,
       b.BookingID
  FROM gen_row g
  JOIN Booking b ON b.BookingID = 1000010 + g.n
  JOIN gen_hotel_params p ON p.hid = b.HotelHotelID
  JOIN gen_room_type t ON t.i = (g.h2 / 17) % 4;

-- Second room on roughly one booking in five (a family taking two rooms).
-- These are the bookings that expose whether the invoice derivation aggregates.
INSERT INTO Room (Room_number, Room_type, Price, HotelHotelID, BookingBookingID)
SELECT 20000 + g.n,
       t.name,
       p.base_price - 20 + (g.h2 / 41) % 41,
       b.HotelHotelID,
       b.BookingID
  FROM gen_row g
  JOIN Booking b ON b.BookingID = 1000010 + g.n
  JOIN gen_hotel_params p ON p.hid = b.HotelHotelID
  JOIN gen_room_type t ON t.i = (g.h / 17) % 4
 WHERE (g.h2 / 23) % 5 = 0;

-- One invoice per booking. Amount left NULL; derived below.
INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
SELECT 3000 + g.n,
       b.BookingID,
       NULL,
       (g.h / 31) % 61,
       b.Checkout_date,
       printf('%02d:%02d', (g.h2 / 53) % 24, (g.h / 59) % 60)
  FROM gen_row g
  JOIN Booking b ON b.BookingID = 1000010 + g.n;

-- Reviews on roughly 70% of bookings that were not cancelled: a guest who
-- never stayed does not review the stay. Rating is the hotel's baseline
-- plus noise of -1/0/+1, clamped to the legal 1..5 range.
INSERT INTO Feedback (FeedbackID, BookingBookingID, Feedback_text, Rating, HotelHotelID)
SELECT 1000 + g.n,
       b.BookingID,
       CASE MAX(1, MIN(5, p.rating_base - 1 + (g.h / 17) % 3))
            WHEN 1 THEN 'Would not stay here again.'
            WHEN 2 THEN 'Below what we expected for the price.'
            WHEN 3 THEN 'Adequate, nothing memorable either way.'
            WHEN 4 THEN 'Good stay, we would come back.'
            ELSE 'Excellent room and genuinely helpful staff.' END,
       MAX(1, MIN(5, p.rating_base - 1 + (g.h / 17) % 3)),
       b.HotelHotelID
  FROM gen_row g
  JOIN Booking b ON b.BookingID = 1000010 + g.n
  JOIN gen_hotel_params p ON p.hid = b.HotelHotelID
 WHERE b.Cancellation = 0
   AND (g.h2 / 29) % 10 < 7;

DROP TABLE gen_row;
DROP TABLE gen_room_type;
DROP TABLE gen_last_name;
DROP TABLE gen_first_name;
DROP TABLE gen_hotel_params;

-- -----------------------------------------------------------------------------
-- Derived columns (mirrors the notebook's business logic in pure SQL):
--   Booking.Duration  = nights between checkout and arrival
--   Invoice.Amount    = Duration * the SUM of the nightly prices of every room
--                       on that booking
--
-- The sum matters. A booking can hold more than one room, and it can hold
-- none. A correlated subquery without an aggregate returns the first matching
-- room only, which silently under-bills every multi-room booking, and returns
-- NULL when a booking has no rooms at all. SUM fixes the first case and
-- COALESCE fixes the second.
-- -----------------------------------------------------------------------------

-- The test suite reads the statements between these two markers straight out of
-- this file and re-runs them, so the regression test exercises the shipped
-- derivation rather than a copy of it. Keep the markers in place.
-- >>> BEGIN DERIVATION >>>
UPDATE Booking
   SET Duration = CAST(julianday(Checkout_date) - julianday(Arrival_date) AS INTEGER);

UPDATE Invoice
   SET Amount = COALESCE((
        SELECT SUM(b.Duration * r.Price)
          FROM Booking b
          JOIN Room    r ON r.BookingBookingID = b.BookingID
         WHERE b.BookingID = Invoice.BookingBookingID
   ), 0);
-- <<< END DERIVATION <<<
