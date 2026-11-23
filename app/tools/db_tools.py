from datetime import date

from app.db import get_connection


def find_exposures(port: str, delay_days: int, today: date | None = None) -> list[dict]:
    """Return open orders at risk from a port disruption, using mock data."""
    today = today or date.today()
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT o.id AS order_id, o.customer, o.quantity, o.due_date,
                   p.id AS product_id, p.sku, p.name AS product_name,
                   i.on_hand_units, i.daily_usage_units,
                   sp.lead_time_days, s.name AS supplier_name, s.port
            FROM orders o
            JOIN products p ON p.id = o.product_id
            JOIN inventory i ON i.product_id = p.id
            JOIN supplier_products sp ON sp.product_id = p.id
            JOIN suppliers s ON s.id = sp.supplier_id
            WHERE o.status = 'open' AND s.port = ? AND s.approved = 1
              AND o.due_date > ?
            """,
            (port, today.isoformat()),
        ).fetchall()
    finally:
        conn.close()

    exposures = []
    for row in rows:
        daily = row["daily_usage_units"] or 1
        days_cover = row["on_hand_units"] / daily
        stockout_day = days_cover - delay_days
        if stockout_day >= row["lead_time_days"]:
            continue
        stockout_days = max(0, round(row["lead_time_days"] + delay_days - days_cover))
        exposures.append(
            {
                "order_id": row["order_id"],
                "customer": row["customer"],
                "sku": row["sku"],
                "product_name": row["product_name"],
                "product_id": row["product_id"],
                "quantity": row["quantity"],
                "due_date": row["due_date"],
                "days_of_cover": round(days_cover, 1),
                "supplier": row["supplier_name"],
                "stockout_days": stockout_days,
            }
        )

    exposures.sort(key=lambda exposure: exposure["stockout_days"], reverse=True)
    return exposures
