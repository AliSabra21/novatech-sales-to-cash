from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW = PROJECT_ROOT / "data" / "raw"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

customers = pd.read_csv(RAW / "customers.csv")
products = pd.read_csv(RAW / "products.csv")

orders = pd.read_csv(
    RAW / "sales_orders.csv",
    parse_dates=["order_date", "requested_delivery_date"]
)

order_items = pd.read_csv(
    RAW / "sales_order_items.csv"
)

deliveries = pd.read_csv(
    RAW / "deliveries.csv",
    parse_dates=["delivery_date"]
)

delivery_items = pd.read_csv(
    RAW / "delivery_items.csv"
)

invoices = pd.read_csv(
    RAW / "invoices.csv",
    parse_dates=["invoice_date", "due_date"]
)

payments = pd.read_csv(
    RAW / "payments.csv",
    parse_dates=["payment_date"]
)


# --------------------------------------------------
# VALIDATION HELPER
# --------------------------------------------------

results = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((name, status))
    print(f"{status:4} | {name}")


print("\nDATA VALIDATION")
print("=" * 70)


# --------------------------------------------------
# PRIMARY KEYS
# --------------------------------------------------

check(
    "customer_id unique",
    customers["customer_id"].is_unique
)

check(
    "product_id unique",
    products["product_id"].is_unique
)

check(
    "sales_order_id unique",
    orders["sales_order_id"].is_unique
)

check(
    "delivery_id unique",
    deliveries["delivery_id"].is_unique
)

check(
    "invoice_id unique",
    invoices["invoice_id"].is_unique
)

check(
    "payment_id unique",
    payments["payment_id"].is_unique
)

check(
    "sales order item key unique",
    not order_items.duplicated(
        ["sales_order_id", "order_item"]
    ).any()
)

check(
    "delivery item key unique",
    not delivery_items.duplicated(
        ["delivery_id", "delivery_item"]
    ).any()
)


# --------------------------------------------------
# FOREIGN KEYS
# --------------------------------------------------

check(
    "orders → customers valid",
    orders["customer_id"].isin(
        customers["customer_id"]
    ).all()
)

check(
    "order items → orders valid",
    order_items["sales_order_id"].isin(
        orders["sales_order_id"]
    ).all()
)

check(
    "order items → products valid",
    order_items["product_id"].isin(
        products["product_id"]
    ).all()
)

check(
    "deliveries → orders valid",
    deliveries["sales_order_id"].isin(
        orders["sales_order_id"]
    ).all()
)

check(
    "delivery items → deliveries valid",
    delivery_items["delivery_id"].isin(
        deliveries["delivery_id"]
    ).all()
)

check(
    "delivery items → products valid",
    delivery_items["product_id"].isin(
        products["product_id"]
    ).all()
)

check(
    "invoices → deliveries valid",
    invoices["delivery_id"].isin(
        deliveries["delivery_id"]
    ).all()
)

check(
    "invoices → customers valid",
    invoices["customer_id"].isin(
        customers["customer_id"]
    ).all()
)

check(
    "payments → invoices valid",
    payments["invoice_id"].isin(
        invoices["invoice_id"]
    ).all()
)


# --------------------------------------------------
# BUSINESS RULES
# --------------------------------------------------

check(
    "all order quantities positive",
    (order_items["ordered_quantity"] > 0).all()
)

check(
    "all delivery quantities positive",
    (delivery_items["delivered_quantity"] > 0).all()
)

check(
    "all prices positive",
    (order_items["unit_price"] > 0).all()
)

check(
    "discounts between 0% and 100%",
    order_items["discount_pct"].between(
        0, 1
    ).all()
)

check(
    "invoice amounts positive",
    (invoices["invoice_amount"] > 0).all()
)

check(
    "payment amounts positive",
    (payments["payment_amount"] > 0).all()
)


# --------------------------------------------------
# DATE LOGIC
# --------------------------------------------------

delivery_dates = deliveries.merge(
    orders[
        ["sales_order_id", "order_date"]
    ],
    on="sales_order_id",
    how="left"
)

check(
    "delivery never before order",
    (
        delivery_dates["delivery_date"]
        >= delivery_dates["order_date"]
    ).all()
)


invoice_dates = invoices.merge(
    deliveries[
        ["delivery_id", "delivery_date"]
    ],
    on="delivery_id",
    how="left"
)

check(
    "invoice never before delivery",
    (
        invoice_dates["invoice_date"]
        >= invoice_dates["delivery_date"]
    ).all()
)

check(
    "due date after invoice date",
    (
        invoices["due_date"]
        >= invoices["invoice_date"]
    ).all()
)


payment_dates = payments.merge(
    invoices[
        ["invoice_id", "invoice_date"]
    ],
    on="invoice_id",
    how="left"
)

check(
    "payment never before invoice",
    (
        payment_dates["payment_date"]
        >= payment_dates["invoice_date"]
    ).all()
)


# --------------------------------------------------
# PAYMENT RECONCILIATION
# --------------------------------------------------

paid = (
    payments
    .groupby("invoice_id")["payment_amount"]
    .sum()
    .reset_index()
)

paid.rename(
    columns={
        "payment_amount": "total_paid"
    },
    inplace=True
)

reconciliation = invoices.merge(
    paid,
    on="invoice_id",
    how="left"
)

reconciliation["total_paid"] = (
    reconciliation["total_paid"]
    .fillna(0)
)

check(
    "no invoice overpaid",
    (
        reconciliation["total_paid"]
        <= reconciliation["invoice_amount"] + 0.02
    ).all()
)


# --------------------------------------------------
# CANCELLED ORDERS
# --------------------------------------------------

cancelled_orders = set(
    orders.loc[
        orders["order_status"] == "Cancelled",
        "sales_order_id"
    ]
)

delivered_orders = set(
    deliveries["sales_order_id"]
)

check(
    "cancelled orders have no delivery",
    cancelled_orders.isdisjoint(
        delivered_orders
    )
)


# --------------------------------------------------
# ONE INVOICE PER DELIVERY
# --------------------------------------------------

check(
    "one invoice per delivery",
    invoices["delivery_id"].is_unique
)


# --------------------------------------------------
# FINAL RESULT
# --------------------------------------------------

failed = [
    name
    for name, status in results
    if status == "FAIL"
]

print("\n" + "=" * 70)

if not failed:
    print("ALL VALIDATION CHECKS PASSED")
else:
    print(f"{len(failed)} VALIDATION CHECK(S) FAILED")

    for name in failed:
        print(" -", name)