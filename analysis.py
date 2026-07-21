"""
Revenue-at-risk analysis for the MAGS hotel-booking platform.

Business question
-----------------
    Which hotels lose the most booked revenue to cancellations, and is that
    loss associated with weak guest ratings?

Cancellations are not evenly spread across a portfolio. A hotel that cancels
often *and* charges a high nightly rate destroys far more revenue than its
booking count suggests, so ranking by cancellation rate alone points management
at the wrong properties. This script ranks by the money involved, then tests
whether guest rating moves with the cancellation rate.

Every figure quoted in the README is produced by this script:

    python analysis.py

NOTE ON THE DATA. The dataset is synthetic and its generator (``sql/seed.sql``)
deliberately gives lower-rated hotels a higher cancellation rate. The negative
correlation reported below is therefore recovered structure, not a discovery
about real hotels. What is being demonstrated is the method.
"""

from __future__ import annotations

import pandas as pd

import db

# Per-hotel aggregation. Revenue is the invoiced Amount, which the seed script
# derives as nights * the summed nightly price of every room on the booking.
HOTEL_SQL = """
    SELECT h.HotelID                                            AS hotel_id,
           h.Name                                               AS hotel,
           COUNT(b.BookingID)                                   AS bookings,
           SUM(b.Cancellation)                                  AS cancelled,
           SUM(i.Amount)                                        AS booked_revenue,
           SUM(CASE WHEN b.Cancellation = 1 THEN i.Amount ELSE 0 END) AS lost_revenue,
           SUM(CASE WHEN b.Cancellation = 0 THEN i.Amount ELSE 0 END) AS realised_revenue,
           (SELECT ROUND(AVG(f.Rating), 2) FROM Feedback f
             WHERE f.HotelHotelID = h.HotelID)                  AS avg_rating,
           (SELECT COUNT(*) FROM Feedback f
             WHERE f.HotelHotelID = h.HotelID)                  AS reviews
      FROM Hotel   h
      JOIN Booking b ON b.HotelHotelID     = h.HotelID
      JOIN Invoice i ON i.BookingBookingID = b.BookingID
     GROUP BY h.HotelID, h.Name
"""


def hotel_revenue_at_risk(conn) -> pd.DataFrame:
    """Per-hotel cancellation rate, revenue lost to cancellations and rating."""
    frame = pd.read_sql_query(HOTEL_SQL, conn)
    frame["cancel_rate_pct"] = (100 * frame["cancelled"] / frame["bookings"]).round(1)
    frame["lost_share_pct"] = (
        100 * frame["lost_revenue"] / frame["booked_revenue"]
    ).round(1)
    return frame.sort_values("lost_revenue", ascending=False).reset_index(drop=True)


def main() -> None:
    conn = db.connect()
    try:
        frame = hotel_revenue_at_risk(conn)

        bookings = int(frame["bookings"].sum())
        booked = int(frame["booked_revenue"].sum())
        lost = int(frame["lost_revenue"].sum())

        print(f"Dataset: {bookings} bookings across {len(frame)} hotels "
              f"(synthetic; see sql/seed.sql).\n")

        print("Revenue at risk from cancellations, worst first")
        print(frame[["hotel", "bookings", "cancel_rate_pct", "booked_revenue",
                     "lost_revenue", "lost_share_pct", "avg_rating", "reviews"]]
              .to_string(index=False))

        print(f"\nPortfolio booked revenue          GBP {booked:,}")
        print(f"Portfolio revenue lost to cancels GBP {lost:,} "
              f"({100 * lost / booked:.1f}% of booked)")

        worst3 = frame.head(3)
        print(f"Top 3 hotels by loss              GBP {int(worst3['lost_revenue'].sum()):,} "
              f"({100 * worst3['lost_revenue'].sum() / lost:.1f}% of all losses, "
              f"{100 * worst3['bookings'].sum() / bookings:.1f}% of bookings)")

        # Does rating move with cancellation rate?
        corr = frame["avg_rating"].corr(frame["cancel_rate_pct"])
        print(f"\nPearson r, avg rating vs cancellation rate: {corr:.3f} "
              f"(n = {len(frame)} hotels)")

        # Ranking by rate alone versus by money: do they point at the same hotel?
        by_rate = frame.sort_values("cancel_rate_pct", ascending=False).iloc[0]
        by_money = frame.iloc[0]
        print(f"Worst by cancellation rate: {by_rate['hotel']} "
              f"({by_rate['cancel_rate_pct']}%, GBP {int(by_rate['lost_revenue']):,} lost)")
        print(f"Worst by revenue lost:      {by_money['hotel']} "
              f"({by_money['cancel_rate_pct']}%, GBP {int(by_money['lost_revenue']):,} lost)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
