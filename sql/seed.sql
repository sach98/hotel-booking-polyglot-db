-- =============================================================================
-- MAGS Hotel Booking Platform - Relational seed script (SQLite)
-- -----------------------------------------------------------------------------
-- Builds the `hotel.db` SQLite database from scratch: 6-table 3NF schema plus
-- a small synthetic sample dataset, so the project is fully reproducible with
-- no manual data entry.
--
--   Usage:  sqlite3 data/hotel.db < sql/seed.sql
--
-- All data below is fictional and generated for demonstration only.
-- Foreign keys are enabled so the sample rows are guaranteed referentially valid.
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
    BookingBookingID INTEGER NOT NULL,
    Amount           INTEGER,                       -- derived: Duration * Price
    Discount         INTEGER,
    Date             TEXT,
    Time             TEXT,
    FOREIGN KEY (BookingBookingID) REFERENCES Booking (BookingID)
);

CREATE TABLE Feedback (
    FeedbackID       INTEGER PRIMARY KEY,
    BookingBookingID INTEGER,
    Feedback_text    TEXT,
    Rating           INTEGER CHECK (Rating BETWEEN 1 AND 5),
    HotelHotelID     INTEGER NOT NULL,
    FOREIGN KEY (BookingBookingID) REFERENCES Booking (BookingID),
    FOREIGN KEY (HotelHotelID)     REFERENCES Hotel   (HotelID)
);

-- -----------------------------------------------------------------------------
-- Sample data (synthetic). Insert parents first, children after.
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

-- -----------------------------------------------------------------------------
-- Derived columns (mirrors the notebook's business logic in pure SQL):
--   Booking.Duration  = nights between checkout and arrival
--   Invoice.Amount    = Booking.Duration * Room.Price for the matching booking
-- -----------------------------------------------------------------------------

UPDATE Booking
   SET Duration = CAST(julianday(Checkout_date) - julianday(Arrival_date) AS INTEGER);

UPDATE Invoice
   SET Amount = (
        SELECT b.Duration * r.Price
          FROM Booking b
          JOIN Room    r ON r.BookingBookingID = b.BookingID
         WHERE b.BookingID = Invoice.BookingBookingID
   );
