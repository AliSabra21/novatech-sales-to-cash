from pathlib import Path
from getpass import getpass

import pandas as pd
import matplotlib.pyplot as plt

from sqlalchemy import create_engine
from sqlalchemy.engine import URL


# --------------------------------------------------
# SETUP
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_PATH = PROJECT_ROOT / "data" / "processed"
DOCS_PATH = PROJECT_ROOT / "documentation"

PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
DOCS_PATH.mkdir(parents=True, exist_ok=True)

REPORTING_DATE = "2026-03-31"


# --------------------------------------------------
# CONNECT TO POSTGRESQL
# --------------------------------------------------

password = getpass("PostgreSQL password: ")

connection_url = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password=password,
    host="localhost",
    port=5432,
    database="novatech_analytics"
)

engine = create_engine(connection_url)


# --------------------------------------------------
# CUSTOMER SALES PERFORMANCE
# --------------------------------------------------

sales_query = """
SELECT
    customer_id,
    customer_name,
    customer_segment,
    country,

    COUNT(DISTINCT sales_order_id) AS order_count,

    SUM(revenue) AS revenue,

    SUM(gross_profit) AS gross_profit,

    100.0 * SUM(gross_profit)
        / NULLIF(SUM(revenue), 0)
        AS gross_margin_pct

FROM vw_sales_lines

GROUP BY
    customer_id,
    customer_name,
    customer_segment,
    country;
"""

sales = pd.read_sql(
    sales_query,
    engine
)


# --------------------------------------------------
# CUSTOMER PAYMENT PERFORMANCE
# --------------------------------------------------

finance_query = """
SELECT
    customer_id,
    COUNT(invoice_id) AS invoice_count,
    SUM(invoice_amount) AS total_invoiced,
    SUM(outstanding_amount) AS outstanding_amount,

    SUM(
        CASE
            WHEN outstanding_amount > 0
             AND due_date < DATE '2026-03-31'
            THEN outstanding_amount
            ELSE 0
        END
    ) AS overdue_amount,

    AVG(
        CASE
            WHEN payment_status = 'Paid'
            THEN payment_delay_days
            ELSE NULL
        END
    ) AS avg_payment_delay_days,

    SUM(
        CASE
            WHEN payment_status = 'Paid'
             AND payment_delay_days > 0
            THEN 1
            ELSE 0
        END
    ) AS late_payment_count
,
100.0 *
SUM(
    CASE
        WHEN payment_status = 'Paid'
         AND payment_delay_days > 0
        THEN 1
        ELSE 0
    END
)
/
NULLIF(
    SUM(
        CASE
            WHEN payment_status = 'Paid'
            THEN 1
            ELSE 0
        END
    ),
    0
) AS late_payment_rate_pct
FROM vw_invoice_status
GROUP BY customer_id
"""
finance = pd.read_sql(
    finance_query,
    engine
)


# --------------------------------------------------
# COMBINE SALES + FINANCE
# --------------------------------------------------

customers = sales.merge(
    finance,
    on="customer_id",
    how="left"
)

numeric_columns = [
    "invoice_count",
    "avg_payment_delay_days",
    "outstanding_amount",
    "overdue_amount",
    "late_payment_rate_pct"
]

customers[numeric_columns] = (
    customers[numeric_columns]
    .fillna(0)
)


# --------------------------------------------------
# BENCHMARKS
# --------------------------------------------------

high_value_threshold = customers[
    "revenue"
].quantile(0.75)

company_margin = (
    customers["gross_profit"].sum()
    / customers["revenue"].sum()
    * 100
)


# --------------------------------------------------
# CUSTOMER CLASSIFICATION
# --------------------------------------------------

def classify_customer(row):

    high_value = (
        row["revenue"]
        >= high_value_threshold
    )

    payment_risk = (
        row["avg_payment_delay_days"] > 10
        or row["overdue_amount"] > 0
    )

    low_margin = (
        row["gross_margin_pct"]
        < company_margin - 5
    )

    if high_value and payment_risk:
        return "High Value / Payment Risk"

    if high_value and low_margin:
        return "Low Margin Key Account"

    if high_value:
        return "High Value / Reliable"

    return "Standard Customer"


customers["customer_profile"] = (
    customers.apply(
        classify_customer,
        axis=1
    )
)


# --------------------------------------------------
# ROUND OUTPUT
# --------------------------------------------------

round_columns = [
    "revenue",
    "gross_profit",
    "gross_margin_pct",
    "avg_payment_delay_days",
    "outstanding_amount",
    "overdue_amount",
    "late_payment_rate_pct"
]

customers[round_columns] = (
    customers[round_columns]
    .round(2)
)


# --------------------------------------------------
# EXPORT ANALYTICAL DATASET
# --------------------------------------------------

customers = customers.sort_values(
    "revenue",
    ascending=False
)

output_file = (
    PROCESSED_PATH
    / "customer_performance.csv"
)

customers.to_csv(
    output_file,
    index=False
)


# --------------------------------------------------
# PYTHON VISUALIZATION
# --------------------------------------------------

plt.figure(figsize=(10, 6))

plt.scatter(
    customers["revenue"],
    customers["avg_payment_delay_days"]
)

plt.xlabel("Customer Revenue (€)")
plt.ylabel("Average Payment Delay (Days)")
plt.title(
    "Customer Value vs Payment Behaviour"
)

plt.tight_layout()

chart_file = (
    DOCS_PATH
    / "customer_value_vs_payment_delay.png"
)

plt.savefig(
    chart_file,
    dpi=150
)

plt.close()


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("\nCUSTOMER ANALYSIS COMPLETED")
print("-----------------------------------")

print(
    f"Customers analysed: "
    f"{len(customers)}"
)

print(
    f"High-value threshold: "
    f"€{high_value_threshold:,.2f}"
)

print(
    f"Company gross margin: "
    f"{company_margin:.2f}%"
)

print("\nCustomer profiles:")

print(
    customers[
        "customer_profile"
    ].value_counts()
)

print("\nTop 10 customers by revenue:")

print(
    customers[
        [
            "customer_name",
            "revenue",
            "gross_margin_pct",
            "avg_payment_delay_days",
            "overdue_amount",
            "customer_profile"
        ]
    ].head(10).to_string(
        index=False
    )
)

print("\nFiles created:")

print(output_file)
print(chart_file)
