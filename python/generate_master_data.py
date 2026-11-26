from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker


# --------------------------------------------------
# SETUP
# --------------------------------------------------

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
Faker.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw"
RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# CUSTOMER MASTER DATA
# --------------------------------------------------

countries = {
    "Germany": {"weight": 0.40, "locale": "de_DE", "region": "DACH"},
    "France": {"weight": 0.15, "locale": "fr_FR", "region": "Western Europe"},
    "Netherlands": {"weight": 0.12, "locale": "nl_NL", "region": "Benelux"},
    "Italy": {"weight": 0.12, "locale": "it_IT", "region": "Southern Europe"},
    "Austria": {"weight": 0.10, "locale": "de_AT", "region": "DACH"},
    "Belgium": {"weight": 0.11, "locale": "fr_FR", "region": "Benelux"},
}

segments = ["Enterprise", "Mid-Market", "SME", "Distributor"]
segment_weights = [0.20, 0.35, 0.35, 0.10]

industries = [
    "Automotive",
    "Industrial Automation",
    "Machinery",
    "Electronics",
    "Energy",
    "Logistics",
]

payment_terms_by_segment = {
    "Enterprise": [30, 45, 60],
    "Mid-Market": [30, 45],
    "SME": [14, 30],
    "Distributor": [30, 45, 60],
}

credit_limit_ranges = {
    "Enterprise": (150000, 500000),
    "Mid-Market": (75000, 200000),
    "SME": (20000, 90000),
    "Distributor": (100000, 300000),
}


def generate_customers(n=120):
    customers = []

    country_names = list(countries.keys())
    country_weights = [countries[c]["weight"] for c in country_names]

    fakers = {
        country: Faker(details["locale"])
        for country, details in countries.items()
    }

    for i in range(1, n + 1):

        country = random.choices(
            country_names,
            weights=country_weights,
            k=1
        )[0]

        segment = random.choices(
            segments,
            weights=segment_weights,
            k=1
        )[0]

        faker = fakers[country]

        min_credit, max_credit = credit_limit_ranges[segment]

        customer = {
            "customer_id": f"C{i:03d}",
            "customer_name": faker.company(),
            "country": country,
            "region": countries[country]["region"],
            "industry": random.choice(industries),
            "customer_segment": segment,
            "payment_terms_days": random.choice(
                payment_terms_by_segment[segment]
            ),
            "credit_limit": round(
                random.randint(min_credit, max_credit) / 1000
            ) * 1000,
            "customer_since": faker.date_between(
                start_date="-10y",
                end_date="-1y"
            ),
        }

        customers.append(customer)

    return pd.DataFrame(customers)


# --------------------------------------------------
# PRODUCT MASTER DATA
# --------------------------------------------------

product_categories = {
    "Sensors": {
        "products": [
            "Temperature Sensor",
            "Pressure Sensor",
            "Proximity Sensor",
            "Optical Sensor",
            "Flow Sensor",
            "Humidity Sensor",
            "Vibration Sensor",
            "Level Sensor",
            "Motion Sensor",
            "Position Sensor",
        ],
        "price_range": (60, 220),
        "cost_ratio": (0.45, 0.65),
    },

    "Controllers": {
        "products": [
            "PLC Control Module",
            "Motion Controller",
            "Motor Controller",
            "Process Controller",
            "Safety Controller",
            "Compact PLC",
            "Remote I/O Controller",
            "PID Controller",
            "Machine Controller",
            "Logic Control Unit",
        ],
        "price_range": (250, 1200),
        "cost_ratio": (0.60, 0.78),
    },

    "Power": {
        "products": [
            "Industrial Power Supply",
            "DIN Rail Power Supply",
            "UPS Module",
            "Voltage Converter",
            "DC Power Module",
            "Power Distribution Unit",
            "Battery Backup Module",
            "AC/DC Converter",
            "Power Controller",
            "Industrial Transformer",
        ],
        "price_range": (90, 550),
        "cost_ratio": (0.52, 0.70),
    },

    "Connectivity": {
        "products": [
            "Industrial Ethernet Cable",
            "M12 Connector",
            "Fieldbus Connector",
            "Industrial Switch",
            "Fiber Optic Cable",
            "I/O Connector",
            "Data Cable",
            "Network Adapter",
            "Terminal Block",
            "Signal Connector",
        ],
        "price_range": (20, 300),
        "cost_ratio": (0.40, 0.62),
    },

    "IoT": {
        "products": [
            "Industrial IoT Gateway",
            "Edge Computing Gateway",
            "Wireless IoT Module",
            "Remote Monitoring Gateway",
            "Data Acquisition Gateway",
            "Smart Factory Gateway",
            "Industrial 5G Module",
            "Telemetry Gateway",
            "Sensor IoT Hub",
            "Edge Analytics Device",
        ],
        "price_range": (350, 1800),
        "cost_ratio": (0.58, 0.75),
    },

    "Automation": {
        "products": [
            "Servo Actuator",
            "Linear Actuator",
            "Industrial Relay",
            "Variable Frequency Drive",
            "Motor Starter",
            "Safety Relay",
            "Robot Interface Module",
            "Automation Interface",
            "Industrial HMI",
            "Remote I/O Module",
        ],
        "price_range": (120, 950),
        "cost_ratio": (0.50, 0.72),
    },
}


suppliers = [
    "NordTech Systems",
    "Alpen Components",
    "Rhein Electronics",
    "Benelux Controls",
    "EuroMotion Industries",
    "Vector Automation",
    "Nexa Industrial",
    "CoreTech Components",
]


def generate_products():
    products = []

    product_counter = 1

    for category, details in product_categories.items():

        for product_name in details["products"]:

            list_price = round(
                random.uniform(*details["price_range"]),
                2
            )

            cost_ratio = random.uniform(
                *details["cost_ratio"]
            )

            standard_cost = round(
                list_price * cost_ratio,
                2
            )

            product = {
                "product_id": f"P{product_counter:03d}",
                "product_name": product_name,
                "product_category": category,
                "list_price": list_price,
                "standard_cost": standard_cost,
                "supplier": random.choice(suppliers),
                "active_status": "Active",
            }

            products.append(product)
            product_counter += 1

    return pd.DataFrame(products)


# --------------------------------------------------
# GENERATE + EXPORT
# --------------------------------------------------

customers_df = generate_customers()
products_df = generate_products()

customers_df.to_csv(
    RAW_DATA_PATH / "customers.csv",
    index=False
)

products_df.to_csv(
    RAW_DATA_PATH / "products.csv",
    index=False
)


# --------------------------------------------------
# QUICK VALIDATION
# --------------------------------------------------

print("\nMASTER DATA GENERATED SUCCESSFULLY")
print("-----------------------------------")
print(f"Customers: {len(customers_df)}")
print(f"Products:  {len(products_df)}")

print("\nCustomers by segment:")
print(customers_df["customer_segment"].value_counts())

print("\nCustomers by country:")
print(customers_df["country"].value_counts())

print("\nProducts by category:")
print(products_df["product_category"].value_counts())

print("\nFiles saved to:")
print(RAW_DATA_PATH)
