"""Contract-style validation for the silver layer: required keys, types and ranges."""
from __future__ import annotations

CONTRACTS = {
    "Suppliers": {
        "key": "SupplierID",
        "fields": {
            "SupplierID": int,
            "CompanyName": str,
            "Country": str,
            "LastModified": str,
        },
        "rules": {"Country": lambda v: len(v) == 2},
    },
    "Products": {
        "key": "ProductID",
        "fields": {
            "ProductID": int,
            "ProductName": str,
            "Category": str,
            "UnitPrice": (int, float),
            "UnitsInStock": int,
            "SupplierID": int,
            "Discontinued": bool,
            "LastModified": str,
        },
        "rules": {"UnitPrice": lambda v: v >= 0, "UnitsInStock": lambda v: v >= 0},
    },
    "Orders": {
        "key": "OrderID",
        "fields": {
            "OrderID": int,
            "ProductID": int,
            "Quantity": int,
            "OrderDate": str,
            "LastModified": str,
        },
        "rules": {"Quantity": lambda v: v > 0},
    },
}


class ContractError(ValueError):
    pass


def validate_rows(entity_set: str, rows: list[dict]) -> list[str]:
    """Return a list of contract violations (empty list means clean)."""
    contract = CONTRACTS[entity_set]
    problems: list[str] = []
    key = contract["key"]
    for i, row in enumerate(rows):
        for field, ftype in contract["fields"].items():
            if field not in row:
                problems.append(f"row {i} ({key}={row.get(key)}): missing field {field}")
            elif not isinstance(row[field], ftype) or (ftype is int and isinstance(row[field], bool)):
                problems.append(f"row {i} ({key}={row.get(key)}): {field} has wrong type")
        for field, rule in contract.get("rules", {}).items():
            if field in row and isinstance(row[field], contract["fields"][field]):
                if not rule(row[field]):
                    problems.append(f"row {i} ({key}={row.get(key)}): rule failed on {field}")
    return problems
