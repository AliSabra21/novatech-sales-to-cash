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
# LOAD EXISTING DATA
# --------------------------------------------------

customers = pd.read_csv(
    RAW_DATA_PATH / "customers.csv"
)

products = pd.read_csv(
    RAW_DATA_PATH / "products.csv"
)

orders = pd.read_csv(
    RAW_DATA_PATH / "sales_orders.csv",
    parse_dates=[
        "order_date",
        "requested_delivery_date"
    ]
)

order_items = pd.read_csv(
    RAW_DATA_PATH / "sales_order_items.csv"
)


# Add product category to order items
order_items = order_items.merge(
    products[
        ["product_id", "product_category"]
    ],
    on="product_id",
    how="left"
)


# Add customer country to orders
orders = orders.merge(
    customers[
        ["customer_id", "country"]
    ],
    on="customer_id",
    how="left"
)


# --------------------------------------------------
# LOGISTICS SETTINGS
# --------------------------------------------------

warehouses = {
    "Germany": "WH-DE01",
    "Austria": "WH-DE01",
    "Netherlands": "WH-NL01",
    "Belgium": "WH-NL01",
    "France": "WH-DE01",
    "Italy": "WH-DE01",
}

carriers = [
    "DHL Freight",
    "DB Schenker",
    "DSV",
    "Kuehne+Nagel",
]


# --------------------------------------------------
# STORAGE
# --------------------------------------------------

deliveries = []
delivery_items = []

delivery_counter = 1


# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def create_delivery(
    sales_order_id,
    delivery_date,
    country,
    status,
    item_quantities
):
    global delivery_counter

    delivery_id = f"DEL{delivery_counter:05d}"

    deliveries.append({
        "delivery_id": delivery_id,
        "sales_order_id": sales_order_id,
        "delivery_date": delivery_date.date(),
        "warehouse": warehouses.get(
            country,
            "WH-DE01"
        ),
        "carrier": random.choice(carriers),
        "delivery_status": status,
    })

    for delivery_item_number, item in enumerate(
        item_quantities,
        start=1
    ):

        delivery_items.append({
            "delivery_id": delivery_id,
            "delivery_item":
                delivery_item_number * 10,
            "sales_order_id":
                sales_order_id,
            "order_item":
                item["order_item"],
            "product_id":
                item["product_id"],
            "delivered_quantity":
                item["delivered_quantity"],
        })

    delivery_counter += 1


# --------------------------------------------------
# GENERATE DELIVERIES
# --------------------------------------------------

for _, order in orders.iterrows():

    sales_order_id = order[
        "sales_order_id"
    ]

    status = order[
        "order_status"
    ]

    # Cancelled orders generate no delivery
    if status == "Cancelled":
        continue

    items = order_items[
        order_items["sales_order_id"]
        == sales_order_id
    ].copy()

    if items.empty:
        continue

    requested_date = order[
        "requested_delivery_date"
    ]

    order_date = order[
        "order_date"
    ]

    year = order_date.year

    country = order["country"]

    has_iot = (
        items["product_category"]
        == "IoT"
    ).any()


    # --------------------------------------------------
    # OPEN ORDERS
    # --------------------------------------------------

    # Some open orders have not shipped yet
    if status == "Open":

        if random.random() < 0.35:
            continue

        # Otherwise partially fulfill the order
        shipment_items = []

        for _, item in items.iterrows():

            qty = int(
                item["ordered_quantity"]
            )

            delivered_qty = max(
                1,
                round(
                    qty
                    * random.uniform(
                        0.40,
                        0.80
                    )
                )
            )

            delivered_qty = min(
                delivered_qty,
                qty
            )

            shipment_items.append({
                "order_item":
                    item["order_item"],
                "product_id":
                    item["product_id"],
                "delivered_quantity":
                    delivered_qty,
            })

        open_delivery_date = (
            requested_date
            + pd.Timedelta(
                days=random.randint(
                    0,
                    5
                )
            )
        )

        create_delivery(
            sales_order_id,
            open_delivery_date,
            country,
            "Partial",
            shipment_items,
        )

        continue


    # --------------------------------------------------
    # COMPLETED ORDERS
    # --------------------------------------------------

    # 2025 operational improvement
    if year == 2024:
        late_probability = 0.18
        partial_probability = 0.16
    else:
        late_probability = 0.11
        partial_probability = 0.11

    # IoT bottleneck
    if has_iot:
        late_probability += 0.15
        partial_probability += 0.18

    # Larger orders slightly more difficult
    if len(items) >= 4:
        late_probability += 0.04
        partial_probability += 0.04


    is_late = (
        random.random()
        < late_probability
    )

    is_partial = (
        random.random()
        < partial_probability
    )


    # --------------------------------------------------
    # DELIVERY DATE
    # --------------------------------------------------

    if is_late:

        if has_iot:
            delay_days = random.randint(
                3,
                12
            )
        else:
            delay_days = random.randint(
                1,
                7
            )

        first_delivery_date = (
            requested_date
            + pd.Timedelta(
                days=delay_days
            )
        )

    else:

        earliest_date = (
            order_date
            + pd.Timedelta(
                days=2
            )
        )

        latest_date = requested_date

        available_days = max(
            0,
            (
                latest_date
                - earliest_date
            ).days
        )

        first_delivery_date = (
            earliest_date
            + pd.Timedelta(
                days=random.randint(
                    0,
                    available_days
                )
            )
        )


    # --------------------------------------------------
    # NORMAL FULL DELIVERY
    # --------------------------------------------------

    if not is_partial:

        shipment_items = []

        for _, item in items.iterrows():

            shipment_items.append({
                "order_item":
                    item["order_item"],
                "product_id":
                    item["product_id"],
                "delivered_quantity":
                    int(
                        item[
                            "ordered_quantity"
                        ]
                    ),
            })

        create_delivery(
            sales_order_id,
            first_delivery_date,
            country,
            "Delivered",
            shipment_items,
        )

        continue


    # --------------------------------------------------
    # PARTIAL DELIVERY
    # --------------------------------------------------

    # Choose one order line to split
    split_item = items.sample(
        n=1
    ).iloc[0]

    first_shipment = []
    second_shipment = []

    for _, item in items.iterrows():

        ordered_qty = int(
            item["ordered_quantity"]
        )

        if (
            item["order_item"]
            == split_item["order_item"]
        ):

            first_qty = round(
                ordered_qty
                * random.uniform(
                    0.55,
                    0.85
                )
            )

            first_qty = max(
                1,
                first_qty
            )

            if first_qty >= ordered_qty:
                first_qty = (
                    ordered_qty - 1
                )

            remaining_qty = (
                ordered_qty
                - first_qty
            )

            first_shipment.append({
                "order_item":
                    item["order_item"],
                "product_id":
                    item["product_id"],
                "delivered_quantity":
                    first_qty,
            })

            second_shipment.append({
                "order_item":
                    item["order_item"],
                "product_id":
                    item["product_id"],
                "delivered_quantity":
                    remaining_qty,
            })

        else:

            first_shipment.append({
                "order_item":
                    item["order_item"],
                "product_id":
                    item["product_id"],
                "delivered_quantity":
                    ordered_qty,
            })


    create_delivery(
        sales_order_id,
        first_delivery_date,
        country,
        "Partial",
        first_shipment,
    )


    # Second shipment happens later
    extra_delay = (
        random.randint(
            3,
            10
        )
        if has_iot
        else random.randint(
            1,
            6
        )
    )

    second_delivery_date = (
        first_delivery_date
        + pd.Timedelta(
            days=extra_delay
        )
    )

    create_delivery(
        sales_order_id,
        second_delivery_date,
        country,
        "Delivered",
        second_shipment,
    )


# --------------------------------------------------
# CREATE DATAFRAMES
# --------------------------------------------------

deliveries_df = pd.DataFrame(
    deliveries
)

delivery_items_df = pd.DataFrame(
    delivery_items
)


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

deliveries_df.to_csv(
    RAW_DATA_PATH
    / "deliveries.csv",
    index=False
)

delivery_items_df.to_csv(
    RAW_DATA_PATH
    / "delivery_items.csv",
    index=False
)


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

print(
    "\nDELIVERY DATA GENERATED SUCCESSFULLY"
)

print(
    "------------------------------------"
)

print(
    f"Deliveries: {len(deliveries_df)}"
)

print(
    f"Delivery Items: "
    f"{len(delivery_items_df)}"
)

print(
    "\nDelivery Status:"
)

print(
    deliveries_df[
        "delivery_status"
    ].value_counts()
)

print(
    "\nAverage deliveries per shipped order:"
)

shipped_orders = (
    deliveries_df[
        "sales_order_id"
    ].nunique()
)

print(
    round(
        len(deliveries_df)
        / shipped_orders,
        2
    )
)

print(
    "\nFiles created:"
)

print(
    RAW_DATA_PATH
    / "deliveries.csv"
)

print(
    RAW_DATA_PATH
    / "delivery_items.csv"
)