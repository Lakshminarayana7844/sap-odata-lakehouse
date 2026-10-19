"""Synthetic SAP-style master and transactional data served by the mock OData API."""
import datetime
import random

random.seed(7)
BASE = datetime.datetime(2026, 8, 1, 8, 0, 0)

CATEGORIES = ["Electronics", "Mechanical", "Hydraulics", "Fasteners", "Sensors"]

SUPPLIERS = [
    {
        "SupplierID": i,
        "CompanyName": name,
        "Country": country,
        "LastModified": (BASE + datetime.timedelta(hours=i * 3)).isoformat() + "Z",
    }
    for i, (name, country) in enumerate(
        [
            ("Aalberts Surface Technologies", "DE"),
            ("Boker Maschinenbau", "DE"),
            ("Conti Components AG", "CH"),
            ("Deltavalve BV", "NL"),
            ("Elbe Werkzeugbau", "DE"),
            ("Fuchs Hydraulik", "AT"),
            ("Grafe Sensorik", "DE"),
            ("Haberl Praezision", "AT"),
        ],
        start=1,
    )
]

PRODUCTS = [
    {
        "ProductID": i,
        "ProductName": f"{cat} Part {i:03d}",
        "Category": cat,
        "UnitPrice": round(random.uniform(4, 600), 2),
        "UnitsInStock": random.randint(0, 500),
        "SupplierID": random.randint(1, len(SUPPLIERS)),
        "Discontinued": random.random() < 0.08,
        "LastModified": (BASE + datetime.timedelta(hours=i * 5)).isoformat() + "Z",
    }
    for i, cat in zip(range(1, 61), (CATEGORIES * 12))
]

ORDERS = [
    {
        "OrderID": 10000 + i,
        "ProductID": random.randint(1, 60),
        "Quantity": random.randint(1, 100),
        "OrderDate": (BASE.date() + datetime.timedelta(days=random.randint(0, 75))).isoformat(),
        "LastModified": (BASE + datetime.timedelta(hours=i * 2)).isoformat() + "Z",
    }
    for i in range(1, 401)
]

ENTITY_SETS = {
    "Suppliers": ("SupplierID", SUPPLIERS),
    "Products": ("ProductID", PRODUCTS),
    "Orders": ("OrderID", ORDERS),
}
