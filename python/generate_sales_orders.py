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
# LOAD MASTER DATA
# --------------------------------------------------

customers = pd.read_csv(RAW_DATA_PATH / "customers.csv")
products = pd.read_csv(RAW_DATA_PATH / "products.csv")


# --------------------------------------------------
# ORDER DATE GENERATION
# --------------------------------------------------

date_range = pd.date_range(
    start="2024-01-01",
    end="2025-12-31",
    freq="D"
)

month_weights = {
    1: 0.75,
    2: 0.80,
    3: 0.95,
    4: 1.00,
    5: 1.00,
    6: 1.05,
    7: 0.90,
    8: 0.85,
    9: 1.05,
    10: 1.20,
    11: 1.35,
    12: 1.40,
}

date_probabilities = np.array(
    [month_weights[d.month] for d in date_range]
)

date_probabilities = (
    date_probabilities / date_probabilities.sum()
)


# --------------------------------------------------
# CUSTOMER ORDER FREQUENCY
# --------------------------------------------------

segment_order_weight = {
    "Enterprise": 1.8,
    "Mid-Market": 1.3,
    "SME": 0.7,
    "Distributor": 1.6,
}

customer_weights = customers[
    "customer_segment"
].map(segment_order_weight)

customer_weights = (
    customer_weights / customer_weights.sum()
)


# --------------------------------------------------
# ORDER SIZE / DISCOUNT LOGIC
# --------------------------------------------------

quantity_ranges = {
    "Enterprise": (20, 150),
    "Mid-Market": (10, 80),
    "SME": (2, 30),
    "Distributor": (25, 180),
}

discount_ranges = {
    "Enterprise": (0.05, 0.18),
    "Mid-Market": (0.02, 0.10),
    "SME": (0.00, 0.06),
    "Distributor": (0.08, 0.20),
}


# --------------------------------------------------
# GENERATE SALES ORDERS
# --------------------------------------------------

N_ORDERS = 4000

sales_orders = []
sales_order_items = []

for order_number in range(1, N_ORDERS + 1):

    customer = customers.sample(
        n=1,
        weights=customer_weights
    ).iloc[0]

    order_date = np.random.choice(
        date_range,
        p=date_probabilities
    )

    order_date = pd.Timestamp(order_date)

    requested_delivery_date = (
        order_date
        + pd.Timedelta(
            days=random.randint(5, 14)
        )
    )

    order_status = random.choices(
        ["Completed", "Open", "Cancelled"],
        weights=[0.95, 0.03, 0.02],
        k=1
    )[0]

    if customer["customer_segment"] == "Distributor":
        sales_channel = random.choices(
            ["Distributor", "Direct"],
            weights=[0.85, 0.15],
            k=1
        )[0]
    else:
        sales_channel = random.choices(
            ["Direct", "Online"],
            weights=[0.92, 0.08],
            k=1
        )[0]

    sales_order_id = f"SO{order_number:05d}"

    sales_orders.append({
        "sales_order_id": sales_order_id,
        "customer_id": customer["customer_id"],
        "order_date": order_date.date(),
        "requested_delivery_date":
            requested_delivery_date.date(),
        "sales_channel": sales_channel,
        "order_status": order_status,
    })

    number_of_items = random.choices(
        [1, 2, 3, 4, 5],
        weights=[0.15, 0.30, 0.30, 0.18, 0.07],
        k=1
    )[0]

    selected_products = products.sample(
        n=number_of_items,
        replace=False
    )

    qty_min, qty_max = quantity_ranges[
        customer["customer_segment"]
    ]

    disc_min, disc_max = discount_ranges[
        customer["customer_segment"]
    ]

    for item_number, (_, product) in enumerate(
        selected_products.iterrows(),
        start=1
    ):

        ordered_quantity = random.randint(
            qty_min,
            qty_max
        )

        discount_pct = round(
            random.uniform(
                disc_min,
                disc_max
            ),
            4
        )

        sales_order_items.append({
            "sales_order_id": sales_order_id,
            "order_item": item_number * 10,
            "product_id": product["product_id"],
            "ordered_quantity": ordered_quantity,
            "unit_price": product["list_price"],
            "discount_pct": discount_pct,
        })


# --------------------------------------------------
# DATAFRAMES
# --------------------------------------------------

orders_df = pd.DataFrame(sales_orders)
items_df = pd.DataFrame(sales_order_items)


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

orders_df.to_csv(
    RAW_DATA_PATH / "sales_orders.csv",
    index=False
)

items_df.to_csv(
    RAW_DATA_PATH / "sales_order_items.csv",
    index=False
)


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

print("\nSALES DATA GENERATED SUCCESSFULLY")
print("---------------------------------")

print(f"Sales Orders: {len(orders_df)}")
print(f"Order Items:  {len(items_df)}")

print("\nOrder Status:")
print(
    orders_df["order_status"].value_counts()
)

print("\nSales Channel:")
print(
    orders_df["sales_channel"].value_counts()
)

print(
    "\nAverage items per order:",
    round(
        len(items_df) / len(orders_df),
        2
    )
)

print("\nFiles created:")
print(RAW_DATA_PATH / "sales_orders.csv")
print(RAW_DATA_PATH / "sales_order_items.csv")