"""
Test Mapping Preview Example
Simulates the exact product shown in the UI mapping preview
"""
import sys
sys.path.insert(0, '.')

from app.workers.normalizer import normalize_product
from app.services.mapping_service import map_to_schema

# Simulated product matching the Mapping Preview UI
PRODUCT = {
    "id": "shirt_001",
    "title": "Premium Cotton T-Shirt - Blue",
    "body_html": "<p>Soft, breathable cotton t-shirt perfect for summer.</p>",
    "description": "Soft, breathable cotton t-shirt perfect for summer.",
    "vendor": "AutoList Fashion",
    "product_type": "T-Shirt",
    "tags": ["cotton", "casual", "summer"],
    "variants": [
        {
            "id": "v1",
            "sku": "PCTS-BLU-S",
            "price": "29.99",
            "option1": "S",
            "inventory_quantity": 50,
        }
    ],
    "images": [
        {"src": "https://example.com/image.jpg"}
    ],
}

# Amazon Shirt Template Schema
SCHEMA = {
    "schema_id": "amazon_shirt_v1",
    "marketplace": "amazon",
    "category": "shirt",
    "columns": [
        {"canonical": "sku", "type": "string", "required": True},
        {"canonical": "parent_sku", "type": "string", "required": False},
        {"canonical": "title", "type": "string", "required": True},
        {"canonical": "brand", "type": "string", "required": True},
        {"canonical": "description", "type": "string", "required": True},
        {"canonical": "fabric", "type": "string", "required": False},
        {"canonical": "color", "type": "string", "required": True},
        {"canonical": "size", "type": "string", "required": True},
        {"canonical": "price", "type": "float", "required": True},
        {"canonical": "main_image_url", "type": "string", "required": True},
    ]
}

print("=" * 70)
print("  MAPPING PREVIEW TEST - Amazon T-Shirt")
print("=" * 70)

# Step 1: Normalize
print("\n1️⃣  Normalizing product...")
normalized = normalize_product(PRODUCT)
print(f"   ✓ Normalized")

# Step 2: Map to schema
print("\n2️⃣  Mapping to amazon_shirt_v1 schema...")
mappings = map_to_schema(normalized, SCHEMA)

# Step 3: Calculate stats
total_fields = len(mappings)
mapped_fields = sum(1 for m in mappings.values() if m.get("value") is not None)
confidences = [m.get("confidence", 0) for m in mappings.values() if m.get("value") is not None]
avg_confidence = sum(confidences) / len(confidences) if confidences else 0

print(f"   ✓ Mapped {mapped_fields}/{total_fields} fields")

# Display results
print("\n" + "=" * 70)
print(f"📊 Mapping Summary")
print("=" * 70)
print(f"Fields Mapped: {mapped_fields} / {total_fields}")
print(f"Avg Confidence: {avg_confidence * 100:.0f}%")
print(f"Template: {SCHEMA['schema_id']}")

print("\n" + "=" * 70)
print("📋 Field Details")
print("=" * 70)

# Sort by confidence
sorted_mappings = sorted(
    mappings.items(),
    key=lambda x: (x[1].get("value") is not None, x[1].get("confidence", 0)),
    reverse=True
)

for field, mapping in sorted_mappings:
    value = mapping.get("value")
    source = mapping.get("source", "unknown")
    confidence = mapping.get("confidence", 0)
    
    # Status
    if confidence >= 0.8:
        status = "🟢 High"
        conf_pct = f"{confidence*100:.0f}%"
    elif confidence >= 0.5:
        status = "🟡 Med "
        conf_pct = f"{confidence*100:.0f}%"
    elif confidence > 0:
        status = "🔴 Low "
        conf_pct = f"{confidence*100:.0f}%"
    else:
        status = "⚪ Miss"
        conf_pct = "0%"
    
    # Format value
    value_str = str(value) if value is not None else "Not mapped"
    if len(value_str) > 40:
        value_str = value_str[:37] + "..."
    
    print(f"{status} {field:18} {conf_pct:5}  {source:30} {value_str}")

# Check parent_sku specifically
print("\n" + "=" * 70)
print("🔍 Parent SKU Check")
print("=" * 70)

parent_sku_mapping = mappings.get("parent_sku", {})
if parent_sku_mapping.get("value"):
    print(f"✅ Parent SKU extracted successfully!")
    print(f"   SKU: {mappings['sku']['value']}")
    print(f"   Parent SKU: {parent_sku_mapping['value']}")
    print(f"   Confidence: {parent_sku_mapping['confidence']*100:.0f}%")
else:
    print(f"❌ Parent SKU not mapped")
    print(f"   This should have been extracted from SKU: {mappings['sku']['value']}")

print("\n" + "=" * 70)
