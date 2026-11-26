from pathlib import Path
import random

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETUP
# --------------------------------------------------

SEED = 42

random.seed(SEED)
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

customers = pd.read_csv(
    RAW_DATA_PATH / "customers.csv"
)

orders = pd.read_csv(
    RAW_DATA_PATH / "sales_orders.csv"
)

order_items = pd.read_csv(
    RAW_DATA_PATH / "sales_order_items.csv"
)

deliveries = pd.read_csv(
    RAW_DATA_PATH / "deliveries.csv",
    parse_dates=["delivery_date"]
)

delivery_items = pd.read_csv(
    RAW_DATA_PATH / "delivery_items.csv"
)


# --------------------------------------------------
# ENRICH DATA
# --------------------------------------------------

# Customer on each sales order
orders_customer = orders[
    ["sales_order_id", "customer_id"]
]

deliveries = deliveries.merge(
    orders_customer,
    on="sales_order_id",
    how="left"
)


# Payment terms
deliveries = deliveries.merge(
    customers[
        [
            "customer_id",
            "payment_terms_days"
        ]
    ],
    on="customer_id",
    how="left"
)


# Add sales price + discount to delivery items
pricing = order_items[
    [
        "sales_order_id",
        "order_item",
        "unit_price",
        "discount_pct"
    ]
]

delivery_items = delivery_items.merge(
    pricing,
    on=[
        "sales_order_id",
        "order_item"
    ],
    how="left"
)


# Calculate commercial value of each shipped line
delivery_items["net_unit_price"] = (
    delivery_items["unit_price"]
    * (
        1
        - delivery_items["discount_pct"]
    )
)

delivery_items["net_value"] = (
    delivery_items["delivered_quantity"]
    * delivery_items["net_unit_price"]
)


# --------------------------------------------------
# DELIVERY TOTALS
# --------------------------------------------------

delivery_totals = (
    delivery_items
    .groupby("delivery_id")["net_value"]
    .sum()
    .reset_index()
)

delivery_totals["net_value"] = (
    delivery_totals["net_value"]
    .round(2)
)

deliveries = deliveries.merge(
    delivery_totals,
    on="delivery_id",
    how="left"
)


# --------------------------------------------------
# GENERATE INVOICES
# --------------------------------------------------

invoices = []

for invoice_number, (_, delivery) in enumerate(
    deliveries.iterrows(),
    start=1
):

    invoice_id = (
        f"INV{invoice_number:05d}"
    )

    # Usually invoice same day or shortly after shipment
    invoice_date = (
        delivery["delivery_date"]
        + pd.Timedelta(
            days=random.choices(
                [0, 1, 2],
                weights=[
                    0.55,
                    0.35,
                    0.10
                ],
                k=1
            )[0]
        )
    )

    payment_terms = int(
        delivery["payment_terms_days"]
    )

    due_date = (
        invoice_date
        + pd.Timedelta(
            days=payment_terms
        )
    )

    invoices.append({
        "invoice_id":
            invoice_id,

        "delivery_id":
            delivery["delivery_id"],

        "sales_order_id":
            delivery["sales_order_id"],

        "customer_id":
            delivery["customer_id"],

        "invoice_date":
            invoice_date.date(),

        "due_date":
            due_date.date(),

        "payment_terms_days":
            payment_terms,

        "invoice_amount":
            round(
                delivery["net_value"],
                2
            ),

        "currency":
            "EUR",
    })


# --------------------------------------------------
# CREATE DATAFRAME
# --------------------------------------------------

invoices_df = pd.DataFrame(
    invoices
)


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

invoices_df.to_csv(
    RAW_DATA_PATH / "invoices.csv",
    index=False
)


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

print(
    "\nINVOICE DATA GENERATED SUCCESSFULLY"
)

print(
    "-----------------------------------"
)

print(
    f"Invoices: {len(invoices_df)}"
)

print(
    "\nTotal invoiced value:"
)

print(
    f"€{invoices_df['invoice_amount'].sum():,.2f}"
)

print(
    "\nAverage invoice value:"
)

print(
    f"€{invoices_df['invoice_amount'].mean():,.2f}"
)

print(
    "\nInvoices by payment terms:"
)

print(
    invoices_df[
        "payment_terms_days"
    ].value_counts().sort_index()
)

print(
    "\nFile created:"
)

print(
    RAW_DATA_PATH / "invoices.csv"
)