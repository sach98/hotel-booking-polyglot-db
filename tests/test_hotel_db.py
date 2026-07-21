"""
Test suite for the MAGS relational core.

Run from the repository root:

    python -m unittest discover -s tests -t .

Every assertion here is against a hand-computed or independently derived
number, not against the shape of the result. The invoice tests in particular
re-run the derivation SQL *read out of ``sql/seed.sql``*, so reverting that
statement to the non-aggregate form turns this suite red.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis  # noqa: E402
import db        # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_SQL = os.path.join(PROJECT_ROOT, "sql", "seed.sql")

BEGIN_MARKER = "-- >>> BEGIN DERIVATION >>>"
END_MARKER = "-- <<< END DERIVATION <<<"

HASH_BEGIN_MARKER = "-- >>> BEGIN HASH >>>"
HASH_END_MARKER = "-- <<< END HASH <<<"


def read_seed() -> str:
    with open(SEED_SQL) as handle:
        return handle.read()


def read_derivation_sql() -> str:
    """Pull the shipped Duration/Amount derivation out of sql/seed.sql."""
    seed = read_seed()
    start = seed.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = seed.index(END_MARKER)
    statements = seed[start:end].strip()
    if not statements:
        raise AssertionError("derivation block in sql/seed.sql is empty")
    return statements


def read_hash_expressions() -> list:
    """Pull the two generated-row hash expressions out of sql/seed.sql."""
    seed = read_seed()
    start = seed.index(HASH_BEGIN_MARKER) + len(HASH_BEGIN_MARKER)
    end = seed.index(HASH_END_MARKER)
    block = seed[start:end].strip()
    expressions = [line.strip().rstrip(",") for line in block.splitlines() if line.strip()]
    if len(expressions) != 2:
        raise AssertionError(
            "expected 2 hash expressions between the markers in sql/seed.sql, found "
            + str(len(expressions))
        )
    return expressions


def read_generated_row_count() -> int:
    """Pull the recursive seq bound the seed generates rows with."""
    match = re.search(r"SELECT n \+ 1 FROM seq WHERE n < (\d+)", read_seed())
    if match is None:
        raise AssertionError("could not find the generator bound in sql/seed.sql")
    return int(match.group(1))


def build_db(path: str) -> sqlite3.Connection:
    """Build a fresh database from the seed script and return a connection."""
    with sqlite3.connect(path) as setup:
        setup.executescript(read_seed())
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class SeededDatabaseTestCase(unittest.TestCase):
    """Base class giving each test its own freshly seeded database file."""

    def setUp(self) -> None:
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "hotel.db")
        self.conn = build_db(self.db_path)
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(self.conn.close)

    def scalar(self, sql: str, params: tuple = ()):
        return self.conn.execute(sql, params).fetchone()[0]


# ---------------------------------------------------------------------------
# (a) Invoice derivation
# ---------------------------------------------------------------------------

class InvoiceDerivationTests(SeededDatabaseTestCase):

    def test_single_room_booking_matches_hand_computed_oracle(self):
        """Booking 1000001: 2019-07-01 to 2019-07-19 is 18 nights at GBP 100."""
        nights, amount = self.conn.execute("""
            SELECT b.Duration, i.Amount
              FROM Booking b JOIN Invoice i ON i.BookingBookingID = b.BookingID
             WHERE b.BookingID = 1000001
        """).fetchone()
        self.assertEqual(nights, 18)
        self.assertEqual(amount, 18 * 100)
        self.assertEqual(amount, 1800)

    def test_two_room_booking_bills_both_rooms(self):
        """Regression test for the under-billing defect.

        Booking 1000001 is 18 nights. Its room costs GBP 100/night. Adding a
        second room at GBP 250/night makes the correct bill
        18 * (100 + 250) = GBP 6,300. The pre-fix derivation used a correlated
        scalar subquery with no aggregate, so it returned the first matching
        room only and billed 18 * 100 = GBP 1,800, under-billing by GBP 4,500.
        """
        self.conn.execute("""
            INSERT INTO Room (Room_number, Room_type, Price, HotelHotelID, BookingBookingID)
            VALUES (101, 'Studio', 250, 4001, 1000001)
        """)
        self.conn.executescript(read_derivation_sql())

        amount = self.scalar(
            "SELECT Amount FROM Invoice WHERE BookingBookingID = 1000001")
        self.assertEqual(amount, 18 * (100 + 250), "invoice must sum every room on the booking")
        self.assertEqual(amount, 6300)
        self.assertNotEqual(amount, 1800, "only the first room was billed: the aggregate is missing")

    def test_booking_with_no_rooms_bills_zero_not_null(self):
        """A booking with no rooms must bill GBP 0. The pre-fix query gave NULL."""
        self.conn.execute("""
            INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation,
                                 Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
            VALUES (1009001, '2024-03-01', '2024-03-06', 0, NULL, 2, 0, 1001, 4001)
        """)
        self.conn.execute("""
            INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
            VALUES (9001, 1009001, NULL, 0, '2024-03-06', '10:00')
        """)
        self.conn.executescript(read_derivation_sql())

        amount = self.scalar("SELECT Amount FROM Invoice WHERE BookingBookingID = 1009001")
        self.assertIsNotNone(amount, "a room-less booking must bill 0, not NULL")
        self.assertEqual(amount, 0)

    def test_three_room_booking_sums_all_three(self):
        """Nine nights across GBP 100 + 250 + 75 rooms = 9 * 425 = GBP 3,825."""
        self.conn.execute("""
            INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation,
                                 Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
            VALUES (1009002, '2024-03-01', '2024-03-10', 0, NULL, 6, 0, 1001, 4001)
        """)
        self.conn.executemany("""
            INSERT INTO Room (Room_number, Room_type, Price, HotelHotelID, BookingBookingID)
            VALUES (?, ?, ?, 4001, 1009002)
        """, [(9101, 'Single', 100), (9102, 'Studio', 250), (9103, 'Single', 75)])
        self.conn.execute("""
            INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
            VALUES (9002, 1009002, NULL, 0, '2024-03-10', '10:00')
        """)
        self.conn.executescript(read_derivation_sql())

        self.assertEqual(
            self.scalar("SELECT Amount FROM Invoice WHERE BookingBookingID = 1009002"),
            9 * (100 + 250 + 75))
        self.assertEqual(
            self.scalar("SELECT Amount FROM Invoice WHERE BookingBookingID = 1009002"),
            3825)

    def test_every_seeded_invoice_matches_an_independent_oracle(self):
        """Recompute all 250 invoices a different way and require agreement."""
        mismatches = self.conn.execute("""
            SELECT i.InvoiceID, i.Amount,
                   b.Duration * (SELECT COALESCE(SUM(r.Price), 0) FROM Room r
                                  WHERE r.BookingBookingID = b.BookingID) AS oracle
              FROM Invoice i JOIN Booking b ON b.BookingID = i.BookingBookingID
             WHERE i.Amount IS NOT oracle
        """).fetchall()
        self.assertEqual(mismatches, [])

    def test_multi_room_bookings_exist_so_the_aggregate_is_exercised(self):
        """The seed must actually contain multi-room bookings, else the fix is untested."""
        multi = self.scalar("""
            SELECT COUNT(*) FROM (
                SELECT BookingBookingID FROM Room
                 WHERE BookingBookingID IS NOT NULL
                 GROUP BY BookingBookingID HAVING COUNT(*) > 1)
        """)
        self.assertEqual(multi, 48)

    def test_naive_derivation_under_bills_the_seed_by_a_known_amount(self):
        """Pin the size of the defect: the non-aggregate form loses GBP 70,248."""
        correct, naive = self.conn.execute("""
            SELECT SUM(i.Amount),
                   SUM(COALESCE((SELECT b2.Duration * r.Price
                                   FROM Booking b2 JOIN Room r ON r.BookingBookingID = b2.BookingID
                                  WHERE b2.BookingID = i.BookingBookingID), 0))
              FROM Invoice i
        """).fetchone()
        self.assertEqual(correct, 402584)
        self.assertEqual(naive, 332336)
        self.assertEqual(correct - naive, 70248)


# ---------------------------------------------------------------------------
# (b) Checkout_date > Arrival_date
# ---------------------------------------------------------------------------

class BookingDateCheckTests(SeededDatabaseTestCase):

    def _insert_booking(self, booking_id: int, arrival: str, checkout: str):
        self.conn.execute("""
            INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation,
                                 Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
            VALUES (?, ?, ?, 0, NULL, 2, 0, 1001, 4001)
        """, (booking_id, arrival, checkout))

    def test_checkout_before_arrival_is_rejected(self):
        """This is the row that used to produce a Duration of -9."""
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_booking(1009010, "2022-04-10", "2022-04-01")

    def test_same_day_checkout_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_booking(1009011, "2022-04-10", "2022-04-10")

    def test_one_night_stay_is_accepted(self):
        """Positive control: the constraint must not reject legitimate bookings."""
        self._insert_booking(1009012, "2022-04-10", "2022-04-11")
        self.conn.executescript(read_derivation_sql())
        self.assertEqual(
            self.scalar("SELECT Duration FROM Booking WHERE BookingID = 1009012"), 1)

    def test_no_seeded_booking_has_a_non_positive_duration(self):
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM Booking WHERE Duration <= 0"), 0)
        self.assertEqual(self.scalar("SELECT MIN(Duration) FROM Booking"), 1)

    def test_updating_a_booking_to_an_impossible_date_is_rejected(self):
        """The constraint must hold on UPDATE, not only on INSERT."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "UPDATE Booking SET Checkout_date = '2019-06-01' WHERE BookingID = 1000001")


# ---------------------------------------------------------------------------
# (c) One invoice and one review per booking
# ---------------------------------------------------------------------------

class CardinalityConstraintTests(SeededDatabaseTestCase):

    def test_second_invoice_for_the_same_booking_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
                VALUES (9091, 1000001, 999, 0, '2019-07-19', '13:00')
            """)

    def test_second_review_for_the_same_booking_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO Feedback (FeedbackID, BookingBookingID, Feedback_text, Rating, HotelHotelID)
                VALUES (9191, 1000001, 'Second review for the same stay.', 5, 4001)
            """)

    def test_unattributed_reviews_are_still_allowed_more_than_once(self):
        """A NULL booking reference is not a duplicate: two must be accepted."""
        self.conn.executemany("""
            INSERT INTO Feedback (FeedbackID, BookingBookingID, Feedback_text, Rating, HotelHotelID)
            VALUES (?, NULL, ?, 3, 4001)
        """, [(9192, "Anonymous review."), (9193, "Another anonymous review.")])
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM Feedback WHERE BookingBookingID IS NULL"), 2)

    def test_seeded_data_holds_one_invoice_and_at_most_one_review_per_booking(self):
        self.assertEqual(self.scalar("""
            SELECT COUNT(*) FROM (SELECT BookingBookingID FROM Invoice
                                   GROUP BY BookingBookingID HAVING COUNT(*) > 1)"""), 0)
        self.assertEqual(self.scalar("""
            SELECT COUNT(*) FROM (SELECT BookingBookingID FROM Feedback
                                   WHERE BookingBookingID IS NOT NULL
                                   GROUP BY BookingBookingID HAVING COUNT(*) > 1)"""), 0)

    def test_a_valid_invoice_for_an_unbilled_booking_is_still_accepted(self):
        """Positive control: UNIQUE must not block the first invoice."""
        self.conn.execute("""
            INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation,
                                 Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
            VALUES (1009020, '2024-05-01', '2024-05-03', 0, 2, 2, 0, 1001, 4001)
        """)
        self.conn.execute("""
            INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
            VALUES (9020, 1009020, 0, 0, '2024-05-03', '10:00')
        """)
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM Invoice WHERE BookingBookingID = 1009020"), 1)


# ---------------------------------------------------------------------------
# Referential integrity (pre-existing strength: keep it covered)
# ---------------------------------------------------------------------------

class ReferentialIntegrityTests(SeededDatabaseTestCase):

    def test_seeded_database_has_no_orphan_rows(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check;").fetchall(), [])

    def test_invoice_for_a_non_existent_booking_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO Invoice (InvoiceID, BookingBookingID, Amount, Discount, Date, Time)
                VALUES (9099, 7777777, 100, 0, '2024-01-01', '10:00')
            """)

    def test_booking_for_a_non_existent_customer_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO Booking (BookingID, Arrival_date, Checkout_date, Cancellation,
                                     Duration, Number_of_guests, Meal, CustomerCustomerID, HotelHotelID)
                VALUES (1009030, '2024-05-01', '2024-05-03', 0, 2, 2, 0, 999999, 4001)
            """)


# ---------------------------------------------------------------------------
# db.py: identifier allow-listing and parameterised values
# ---------------------------------------------------------------------------

class IdentifierAllowListTests(SeededDatabaseTestCase):

    def test_unknown_table_is_rejected(self):
        with self.assertRaises(ValueError):
            db.get_table(self.conn, "Customer; DROP TABLE Hotel")

    def test_unknown_column_is_rejected(self):
        with self.assertRaises(ValueError):
            db.get_unique(self.conn, "Customer", "CustomerID FROM Customer UNION SELECT 1")

    def test_wrong_value_count_is_rejected(self):
        with self.assertRaises(ValueError):
            db.insert_row(self.conn, "Hotel", [4099, "Too Few Columns"])

    def test_malicious_value_is_stored_as_data_not_executed(self):
        """The injection demonstration, asserted rather than printed."""
        malicious = "Smith'); DROP TABLE Hotel;--"
        db.update_value(self.conn, "Customer", "CustomerID", 1001, "Last_name", malicious)

        self.assertEqual(self.scalar("SELECT COUNT(*) FROM Hotel"), 10)
        self.assertEqual(
            self.scalar("SELECT Last_name FROM Customer WHERE CustomerID = 1001"),
            malicious)

    def test_schema_allow_list_matches_the_delivered_tables(self):
        delivered = {row[0] for row in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(set(db.SCHEMA), delivered)

    def test_schema_allow_list_columns_match_the_delivered_columns(self):
        for table, columns in db.SCHEMA.items():
            actual = [row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")]
            self.assertEqual(columns, actual, f"column list drifted for {table}")


# ---------------------------------------------------------------------------
# (e) Enough data to analyse, and an analysis that answers something
# ---------------------------------------------------------------------------

class AnalysisTests(SeededDatabaseTestCase):

    def test_seed_carries_enough_bookings_to_analyse(self):
        self.assertGreaterEqual(self.scalar("SELECT COUNT(*) FROM Booking"), 200)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM Booking"), 250)

    def test_bookings_per_hotel_is_no_longer_one_everywhere(self):
        """The old dataset returned exactly 1 booking for all ten hotels."""
        per_hotel = [row[0] for row in self.conn.execute(
            "SELECT COUNT(*) FROM Booking GROUP BY HotelHotelID")]
        self.assertEqual(len(per_hotel), 10)
        self.assertGreater(min(per_hotel), 1)
        self.assertEqual(min(per_hotel), 18)
        self.assertEqual(max(per_hotel), 31)

    def test_revenue_splits_exactly_into_lost_and_realised(self):
        """Accounting identity: every booked pound is either lost or realised."""
        frame = analysis.hotel_revenue_at_risk(self.conn)
        for _, row in frame.iterrows():
            self.assertEqual(row["booked_revenue"],
                             row["lost_revenue"] + row["realised_revenue"],
                             f"revenue does not reconcile for {row['hotel']}")

    def test_portfolio_totals_match_the_invoice_table(self):
        frame = analysis.hotel_revenue_at_risk(self.conn)
        self.assertEqual(int(frame["booked_revenue"].sum()),
                         self.scalar("SELECT SUM(Amount) FROM Invoice"))
        self.assertEqual(int(frame["booked_revenue"].sum()), 402584)
        self.assertEqual(int(frame["bookings"].sum()), 250)

    def test_lost_revenue_matches_an_independently_computed_figure(self):
        frame = analysis.hotel_revenue_at_risk(self.conn)
        oracle = self.scalar("""
            SELECT SUM(i.Amount) FROM Invoice i
              JOIN Booking b ON b.BookingID = i.BookingBookingID
             WHERE b.Cancellation = 1
        """)
        self.assertEqual(int(frame["lost_revenue"].sum()), oracle)
        self.assertEqual(int(frame["lost_revenue"].sum()), 56558)

    def test_worst_hotel_by_rate_differs_from_worst_by_money(self):
        """The finding the analysis exists to surface.

        Ranking hotels by cancellation rate points at The Montana (30.0%,
        GBP 3,125 lost). Ranking by money points at Hampton by Hilton London
        Waterloo (27.6%, GBP 22,563 lost). Rate alone misdirects management.
        """
        frame = analysis.hotel_revenue_at_risk(self.conn)
        by_money = frame.iloc[0]
        by_rate = frame.sort_values("cancel_rate_pct", ascending=False).iloc[0]

        self.assertEqual(by_money["hotel"], "Hampton by Hilton London Waterloo")
        self.assertEqual(int(by_money["lost_revenue"]), 22563)
        self.assertEqual(by_rate["hotel"], "The Montana")
        self.assertEqual(int(by_rate["lost_revenue"]), 3125)
        self.assertNotEqual(by_money["hotel"], by_rate["hotel"])

    def test_rating_is_negatively_correlated_with_cancellation_rate(self):
        """Recovers the relationship the generator injects (see sql/seed.sql)."""
        frame = analysis.hotel_revenue_at_risk(self.conn)
        corr = frame["avg_rating"].corr(frame["cancel_rate_pct"])
        self.assertLess(corr, -0.7)
        self.assertAlmostEqual(corr, -0.841, places=3)

    def test_every_hotel_has_enough_reviews_to_average(self):
        counts = [row[0] for row in self.conn.execute(
            "SELECT COUNT(*) FROM Feedback GROUP BY HotelHotelID")]
        self.assertEqual(len(counts), 10)
        self.assertGreaterEqual(min(counts), 8)


# ---------------------------------------------------------------------------
# The seed script is deterministic
# ---------------------------------------------------------------------------

class ReproducibilityTests(unittest.TestCase):

    def test_two_independent_builds_are_identical(self):
        import tempfile

        fingerprints = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                conn = build_db(os.path.join(tmp, "hotel.db"))
                fingerprints.append(conn.execute("""
                    SELECT (SELECT group_concat(CustomerID || First_name || Last_name || Age) FROM Customer)
                        || (SELECT group_concat(BookingID || Arrival_date || Checkout_date
                                                || Cancellation || Duration || HotelHotelID) FROM Booking)
                        || (SELECT group_concat(Room_number || Price || HotelHotelID) FROM Room)
                        || (SELECT group_concat(InvoiceID || Amount || Discount) FROM Invoice)
                        || (SELECT group_concat(FeedbackID || Rating) FROM Feedback)
                """).fetchone()[0])
                conn.close()
        self.assertEqual(fingerprints[0], fingerprints[1])

    def test_generated_hashes_never_overflow_into_floats(self):
        """A 64-bit overflow silently turns the hash into a float and destroys
        the low-order digits that every generated field reads. Both expressions
        and the row bound are read out of sql/seed.sql, so reverting the seed to
        the unreduced product turns this test red instead of leaving it asserting
        against a private copy."""
        first, second = read_hash_expressions()
        bound = read_generated_row_count()
        conn = sqlite3.connect(":memory:")
        try:
            types = conn.execute(f"""
                WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < {bound})
                SELECT DISTINCT typeof({first}), typeof({second})
                  FROM seq
            """).fetchall()
            self.assertEqual(types, [("integer", "integer")])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
