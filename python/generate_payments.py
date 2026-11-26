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

# Financial snapshot date for the project
REPORTING_DATE = pd.Timestamp("2026-03-31")


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

customers = pd.read_csv(
    RAW_DATA_PATH / "customers.csv"
)

invoices = pd.read_csv(
    RAW_DATA_PATH / "invoices.csv",
    parse_dates=[
        "invoice_date",
        "due_date"
    ]
)


# --------------------------------------------------
# ASSIGN CUSTOMER PAYMENT BEHAVIOUR
# --------------------------------------------------

customer_profiles = {}

for customer_id in customers["customer_id"]:

    profile = random.choices(
        [
            "Reliable",
            "Normal",
            "Slow",
            "Risky"
        ],
        weights=[
            0.55,
            0.30,
            0.12,
            0.03
        ],
        k=1
    )[0]

    customer_profiles[
        customer_id
    ] = profile


# --------------------------------------------------
# PAYMENT SETTINGS
# --------------------------------------------------

payment_methods = [
    "Bank Transfer",
    "SEPA Transfer",
    "Direct Debit"
]

payment_method_weights = [
    0.78,
    0.17,
    0.05
]


# --------------------------------------------------
# STORAGE
# --------------------------------------------------

payments = []

payment_counter = 1


def add_payment(
    invoice_id,
    payment_date,
    amount
):

    global payment_counter

    # Do not record future payments
    if payment_date > REPORTING_DATE:
        return

    payments.append({
        "payment_id":
            f"PAY{payment_counter:06d}",

        "invoice_id":
            invoice_id,

        "payment_date":
            payment_date.date(),

        "payment_amount":
            round(amount, 2),

        "payment_method":
            random.choices(
                payment_methods,
                weights=
                    payment_method_weights,
                k=1
            )[0],
    })

    payment_counter += 1


# --------------------------------------------------
# GENERATE PAYMENTS
# --------------------------------------------------

for _, invoice in invoices.iterrows():

    invoice_id = invoice[
        "invoice_id"
    ]

    customer_id = invoice[
        "customer_id"
    ]

    invoice_amount = float(
        invoice["invoice_amount"]
    )

    invoice_date = invoice[
        "invoice_date"
    ]

    due_date = invoice[
        "due_date"
    ]

    profile = customer_profiles[
        customer_id
    ]


    # ----------------------------------------------
    # PAYMENT BEHAVIOUR BY PROFILE
    # ----------------------------------------------

    if profile == "Reliable":

        outcome = random.choices(
            [
                "Full",
                "Partial",
                "Unpaid"
            ],
            weights=[
                0.985,
                0.010,
                0.005
            ],
            k=1
        )[0]

        payment_delay = random.randint(
            -10,
            5
        )


    elif profile == "Normal":

        outcome = random.choices(
            [
                "Full",
                "Partial",
                "Unpaid"
            ],
            weights=[
                0.95,
                0.035,
                0.015
            ],
            k=1
        )[0]

        payment_delay = random.randint(
            -3,
            15
        )


    elif profile == "Slow":

        outcome = random.choices(
            [
                "Full",
                "Partial",
                "Unpaid"
            ],
            weights=[
                0.86,
                0.10,
                0.04
            ],
            k=1
        )[0]

        payment_delay = random.randint(
            8,
            40
        )


    else:  # Risky

        outcome = random.choices(
            [
                "Full",
                "Partial",
                "Unpaid"
            ],
            weights=[
                0.68,
                0.20,
                0.12
            ],
            k=1
        )[0]

        payment_delay = random.randint(
            20,
            70
        )


    # ----------------------------------------------
    # UNPAID
    # ----------------------------------------------

    if outcome == "Unpaid":
        continue


    main_payment_date = (
        due_date
        + pd.Timedelta(
            days=payment_delay
        )
    )

    # Payment cannot happen before invoice exists
    if main_payment_date < invoice_date:

        main_payment_date = (
            invoice_date
            + pd.Timedelta(
                days=random.randint(
                    1,
                    5
                )
            )
        )


    # ----------------------------------------------
    # PARTIAL PAYMENT
    # ----------------------------------------------

    if outcome == "Partial":

        paid_percentage = random.uniform(
            0.30,
            0.80
        )

        amount = (
            invoice_amount
            * paid_percentage
        )

        add_payment(
            invoice_id,
            main_payment_date,
            amount
        )

        continue


    # ----------------------------------------------
    # FULL PAYMENT
    # ----------------------------------------------

    # Some customers pay one invoice
    # using two separate transfers

    split_probability = 0.12

    if random.random() < split_probability:

        first_percentage = random.uniform(
            0.35,
            0.70
        )

        first_amount = (
            invoice_amount
            * first_percentage
        )

        second_amount = (
            invoice_amount
            - first_amount
        )

        first_payment_date = (
            main_payment_date
            - pd.Timedelta(
                days=random.randint(
                    2,
                    10
                )
            )
        )

        if first_payment_date < invoice_date:

            first_payment_date = (
                invoice_date
                + pd.Timedelta(days=1)
            )

        add_payment(
            invoice_id,
            first_payment_date,
            first_amount
        )

        second_payment_date = (
            main_payment_date
            + pd.Timedelta(
                days=random.randint(
                    1,
                    8
                )
            )
        )

        add_payment(
            invoice_id,
            second_payment_date,
            second_amount
        )

    else:

        add_payment(
            invoice_id,
            main_payment_date,
            invoice_amount
        )


# --------------------------------------------------
# DATAFRAME
# --------------------------------------------------

payments_df = pd.DataFrame(
    payments
)


# --------------------------------------------------
# EXPORT
# --------------------------------------------------

payments_df.to_csv(
    RAW_DATA_PATH / "payments.csv",
    index=False
)


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

paid_by_invoice = (
    payments_df
    .groupby("invoice_id")[
        "payment_amount"
    ]
    .sum()
    .reset_index()
)

paid_by_invoice.rename(
    columns={
        "payment_amount":
            "paid_amount"
    },
    inplace=True
)

validation = invoices.merge(
    paid_by_invoice,
    on="invoice_id",
    how="left"
)

validation[
    "paid_amount"
] = validation[
    "paid_amount"
].fillna(0)

validation[
    "outstanding_amount"
] = (
    validation["invoice_amount"]
    - validation["paid_amount"]
)

validation[
    "outstanding_amount"
] = (
    validation[
        "outstanding_amount"
    ].clip(lower=0)
)


total_invoiced = (
    validation[
        "invoice_amount"
    ].sum()
)

total_paid = (
    validation[
        "paid_amount"
    ].sum()
)

total_outstanding = (
    validation[
        "outstanding_amount"
    ].sum()
)


print(
    "\nPAYMENT DATA GENERATED SUCCESSFULLY"
)

print(
    "-----------------------------------"
)

print(
    f"Payments: {len(payments_df)}"
)

print(
    f"\nTotal invoiced: "
    f"€{total_invoiced:,.2f}"
)

print(
    f"Total paid: "
    f"€{total_paid:,.2f}"
)

print(
    f"Outstanding: "
    f"€{total_outstanding:,.2f}"
)

print(
    f"Collection rate: "
    f"{(total_paid / total_invoiced) * 100:.2f}%"
)

print(
    "\nInvoices with zero payment:"
)

print(
    (
        validation[
            "paid_amount"
        ] == 0
    ).sum()
)

print(
    "\nInvoices with partial payment:"
)

print(
    (
        (
            validation[
                "paid_amount"
            ] > 0
        )
        &
        (
            validation[
                "outstanding_amount"
            ] > 0.01
        )
    ).sum()
)

print(
    "\nReporting date:"
)

print(
    REPORTING_DATE.date()
)

print(
    "\nFile created:"
)

print(
    RAW_DATA_PATH
    / "payments.csv"
)