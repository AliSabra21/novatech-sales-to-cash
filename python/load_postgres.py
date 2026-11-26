from pathlib import Path
from getpass import getpass
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"

password = getpass("PostgreSQL password: ")

conn = psycopg2.connect(
    dbname="novatech_analytics",
    user="postgres",
    password=password,
    host="localhost",
    port="5432"
)

tables = [
    "customers",
    "products",
    "sales_orders",
    "sales_order_items",
    "deliveries",
    "delivery_items",
    "invoices",
    "payments"
]

with conn.cursor() as cur:

    cur.execute("""
        TRUNCATE TABLE
        payments,
        invoices,
        delivery_items,
        deliveries,
        sales_order_items,
        sales_orders,
        products,
        customers
        CASCADE;
    """)

    for table in tables:

        file_path = RAW / f"{table}.csv"

        with open(file_path, "r", encoding="utf-8") as file:
            cur.copy_expert(
                f"""
                COPY {table}
                FROM STDIN
                WITH (
                    FORMAT CSV,
                    HEADER TRUE
                )
                """,
                file
            )

        print(f"Loaded: {table}")

conn.commit()
conn.close()

print("\nALL TABLES LOADED SUCCESSFULLY")
