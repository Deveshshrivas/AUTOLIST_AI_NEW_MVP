"""Test parent SKU generation for different patterns"""
import re

def extract_parent_sku(sku: str):
    """Test the parent SKU extraction logic"""
    patterns = [
        r"^([A-Z0-9]+)[-_]",  # PCTS-BLU-S -> PCTS
        r"^([A-Z]+\d+)",       # K001MBLUE -> K001
    ]
    
    for pattern in patterns:
        match = re.match(pattern, str(sku).upper())
        if match:
            return match.group(1)
    return None

# Test cases
test_skus = [
    "PCTS-BLU-S",
    "K001-M-BLUE",
    "SHIRT_RED_L",
    "ABC123-XL-GREEN",
    "KURTA001",
]

print("Testing Parent SKU Generation:")
print("=" * 60)

for sku in test_skus:
    parent = extract_parent_sku(sku)
    print(f"{sku:20} -> {parent if parent else 'NOT FOUND'}")

print("\n" + "=" * 60)
print("\nNow testing with actual mapping service:")
print("=" * 60)

from app.services.mapping_service import map_single_field

# Simulate product data
product = {
    "variants_simplified": [
        {"sku": "PCTS-BLU-S"}
    ]
}

result = map_single_field(product, "parent_sku", "string", None)
print(f"\nSKU: PCTS-BLU-S")
print(f"Parent SKU: {result.value}")
print(f"Source: {result.source}")
print(f"Confidence: {result.confidence}")
