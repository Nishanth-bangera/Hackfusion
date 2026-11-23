from app.db import get_connection, init_db

# All business data below is MOCK data for a fictional company.
# The agents, tools and research are real; the company is not.

SUPPLIERS = [
    # id, name, city, port, approved
    (1, "Shanghai Cells Ltd (MOCK)", "Shenzhen", "Shanghai", 1),
    (2, "Chennai Components Pvt (MOCK)", "Chennai", "Chennai", 1),
    (3, "Hanoi Parts Co (MOCK)", "Hanoi", "Haiphong", 1),
    (4, "Unvetted Trader (MOCK)", "Guangzhou", "Guangzhou", 0),  # not approved
]

PRODUCTS = [
    # id, sku, name
    (1, "CELL-18650", "18650 Li-ion Cell (MOCK)"),
    (2, "BMS-40A", "40A Battery Management Board (MOCK)"),
    (3, "CASE-IP67", "IP67 Battery Enclosure (MOCK)"),
]

SUPPLIER_PRODUCTS = [
    # supplier_id, product_id, unit_price_inr, lead_time_days, capacity_units
    (1, 1, 118.0, 5, 50000),   # Shanghai: 5-day lead time (MOCK)
    (1, 2, 840.0, 5, 3000),
    (1, 3, 200.0, 9, 4000),
    (2, 1, 128.0, 3, 20000),
    (2, 2, 880.0, 4, 2000),
    (3, 1, 122.0, 7, 30000),
    (3, 3, 225.0, 9, 5000),
    (4, 1, 90.0, 5, 10000),  # cheap, but this supplier is not approved
]

INVENTORY = [
    # product_id, on_hand_units, daily_usage_units
    (1, 4800, 800),   # 6 days of cover
    (2, 360, 60),     # 6 days of cover
    (3, 1200, 100),   # 12 days of cover
]

ORDERS = [
    # id, product_id, quantity, customer, due_date, status
    (1, 1, 6000, "MOCK Customer A", "2026-12-05", "open"),
    (2, 2, 500, "MOCK Customer B", "2026-12-10", "open"),
    (3, 1, 2000, "MOCK Customer C", "2026-11-30", "open"),
    (4, 3, 1200, "MOCK Customer D", "2026-12-15", "open"),
]


def seed() -> None:
    init_db()
    conn = get_connection()
    try:
        # Reset only the mock business data so the script can be re-run safely.
        # Job and action history is kept.
        conn.executescript("""
            DELETE FROM orders;
            DELETE FROM inventory;
            DELETE FROM supplier_products;
            DELETE FROM products;
            DELETE FROM suppliers;
        """)

        conn.executemany(
            "INSERT INTO suppliers (id, name, city, port, approved) VALUES (?, ?, ?, ?, ?)",
            SUPPLIERS,
        )
        conn.executemany(
            "INSERT INTO products (id, sku, name) VALUES (?, ?, ?)",
            PRODUCTS,
        )
        conn.executemany(
            "INSERT INTO supplier_products (supplier_id, product_id, unit_price_inr, lead_time_days, capacity_units) "
            "VALUES (?, ?, ?, ?, ?)",
            SUPPLIER_PRODUCTS,
        )
        conn.executemany(
            "INSERT INTO inventory (product_id, on_hand_units, daily_usage_units) VALUES (?, ?, ?)",
            INVENTORY,
        )
        conn.executemany(
            "INSERT INTO orders (id, product_id, quantity, customer, due_date, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ORDERS,
        )
        conn.commit()
        print(
            f"Seeded MOCK data: {len(SUPPLIERS)} suppliers, {len(PRODUCTS)} products, "
            f"{len(ORDERS)} orders."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
