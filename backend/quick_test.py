"""Quick test of parent SKU extraction"""
import sys
sys.path.insert(0, '.')

# Test the regex directly
import re

sku = "PCTS-BLU-S"
patterns = [
    r"^([A-Z0-9]+)[-_]",  # PCTS-BLU-S -> PCTS
    r"^([A-Z]+\d+)",       # K001MBLUE -> K001
]

print(f"Testing SKU: {sku}")
print("=" * 50)

for i, pattern in enumerate(patterns, 1):
    match = re.match(pattern, sku.upper())
    if match:
        print(f"✅ Pattern {i} matched: {pattern}")
        print(f"   Extracted: {match.group(1)}")
        break
    else:
        print(f"❌ Pattern {i} no match: {pattern}")

# Now test with the mapping service
print("\n" + "=" * 50)
print("Testing with mapping service:")
print("=" * 50)

try:
    from app.services.mapping_service import map_single_field

    product = {
        "variants_simplified": [
            {"sku": "PCTS-BLU-S"}
        ]
    }

    result = map_single_field(product, "parent_sku", "string", None)
    
    print(f"\n✅ Result:")
    print(f"   Value: {result.value}")
    print(f"   Source: {result.source}")
    print(f"   Confidence: {result.confidence:.2f}")
    
    if result.value == "PCTS":
        print("\n🎉 SUCCESS! Parent SKU correctly extracted!")
    else:
        print(f"\n❌ FAILED! Expected 'PCTS', got '{result.value}'")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
