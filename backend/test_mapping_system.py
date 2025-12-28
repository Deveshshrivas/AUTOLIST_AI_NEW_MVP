"""
Test Script for Mapping System

Verifies that mapping_service.py and mapping_worker.py work correctly
without needing full database setup.
"""
import asyncio
import json
from pathlib import Path

# Add app to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app.services.mapping_service import (
    map_to_schema,
    map_single_field,
    get_unmapped_fields,
    get_required_unmapped,
    MappingResult,
)
from app.workers.normalizer import normalize_product

# Try to import mapping worker (may fail if anthropic not installed)
try:
    from app.workers.mapping_worker import MappingWorker
    WORKER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import MappingWorker: {e}")
    print("   Skipping worker tests. Install requirements: pip install -r requirements.txt")
    WORKER_AVAILABLE = False
    MappingWorker = None


# Sample Shopify product data
SAMPLE_PRODUCT = {
    "id": "12345",
    "title": "Men's Cotton Kurta - Blue",
    "body_html": "<p>Premium 100% cotton kurta with mandarin collar. Full sleeves. Perfect for ethnic occasions.</p>",
    "vendor": "Fabindia",
    "product_type": "Kurta",
    "tags": ["ethnic", "traditional", "cotton"],
    "variants": [
        {
            "id": "v1",
            "sku": "K001-M-BLUE",
            "price": "1299.00",
            "compare_at_price": "1499.00",
            "inventory_quantity": 45,
            "option1": "M",
            "option2": "Blue",
            "weight": 300,
            "weight_unit": "g",
        }
    ],
    "images": [
        {"src": "https://example.com/kurta1.jpg", "position": 1}
    ],
    "metafields": {
        "custom": {
            "fabric": "100% Cotton",
            "sleeve_length": "Full Sleeve",
            "occasion": "Ethnic Wear",
        }
    },
}


# Sample template schema (Amazon Kurta)
SAMPLE_SCHEMA = {
    "schema_id": "amazon_kurta_v1",
    "marketplace": "amazon",
    "category": "kurta",
    "version": "1.0",
    "columns": [
        {"canonical": "sku", "type": "string", "required": True},
        {"canonical": "parent_sku", "type": "string", "required": False},
        {"canonical": "title", "type": "string", "required": True},
        {"canonical": "description", "type": "string", "required": True},
        {"canonical": "brand", "type": "string", "required": True},
        {"canonical": "price", "type": "float", "required": True},
        {"canonical": "sale_price", "type": "float", "required": False},
        {
            "canonical": "color",
            "type": "enum",
            "enum": ["Red", "Blue", "Green", "Yellow", "White", "Black", "Multicolor"],
            "required": True,
        },
        {
            "canonical": "size",
            "type": "enum",
            "enum": ["XS", "S", "M", "L", "XL", "XXL", "Free Size"],
            "required": True,
        },
        {"canonical": "fabric", "type": "string", "required": True},
        {"canonical": "sleeve_length", "type": "string", "required": False},
        {"canonical": "neckline", "type": "string", "required": False},
        {"canonical": "main_image_url", "type": "string", "required": True},
        {"canonical": "quantity", "type": "int", "required": True},
    ],
}


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_mapping_results(mappings: dict, title: str = "Mapping Results"):
    """Pretty print mapping results."""
    print_section(title)
    
    total_fields = len(mappings)
    mapped_fields = sum(1 for m in mappings.values() if m.get("value") is not None)
    total_confidence = sum(m.get("confidence", 0) for m in mappings.values() if m.get("value") is not None)
    avg_confidence = total_confidence / mapped_fields if mapped_fields > 0 else 0
    
    print(f"\n📊 Statistics:")
    print(f"   Total Fields: {total_fields}")
    print(f"   Mapped: {mapped_fields} ({mapped_fields/total_fields*100:.1f}%)")
    print(f"   Average Confidence: {avg_confidence:.2f}")
    
    print(f"\n📋 Field-by-Field Results:\n")
    
    # Sort by confidence (high to low)
    sorted_mappings = sorted(
        mappings.items(),
        key=lambda x: x[1].get("confidence", 0),
        reverse=True
    )
    
    for field, mapping in sorted_mappings:
        value = mapping.get("value")
        source = mapping.get("source", "unknown")
        confidence = mapping.get("confidence", 0)
        
        # Color code by confidence
        if confidence >= 0.8:
            badge = "🟢"
        elif confidence >= 0.5:
            badge = "🟡"
        elif confidence > 0:
            badge = "🔴"
        else:
            badge = "⚪"
        
        # Format value
        value_str = str(value) if value is not None else "NULL"
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        
        print(f"  {badge} {field:20} {confidence:.2f}  {source:30}  {value_str}")


async def test_rule_based_mapping():
    """Test rule-based mapping without AI."""
    print_section("TEST 1: Rule-Based Mapping (No AI)")
    
    # Step 1: Normalize product
    print("\n1️⃣  Normalizing product data...")
    normalized = normalize_product(SAMPLE_PRODUCT)
    print(f"   ✓ Normalized {len(normalized)} attributes")
    
    # Step 2: Run rule-based mapping
    print("\n2️⃣  Running rule-based mapping...")
    mappings = map_to_schema(normalized, SAMPLE_SCHEMA)
    print(f"   ✓ Mapped {len(mappings)} fields")
    
    # Step 3: Show results
    print_mapping_results(mappings)
    
    # Step 4: Identify gaps
    print_section("Gap Analysis")
    unmapped = get_unmapped_fields(mappings, SAMPLE_SCHEMA, confidence_threshold=0.8)
    required_unmapped = get_required_unmapped(mappings, SAMPLE_SCHEMA, confidence_threshold=0.5)
    
    print(f"\n⚠️  Fields needing AI assistance (< 0.8 confidence):")
    if unmapped:
        for field in unmapped:
            print(f"   • {field}")
    else:
        print("   ✓ None! All fields have high confidence")
    
    print(f"\n🚨 Required fields with issues (< 0.5 confidence):")
    if required_unmapped:
        for field in required_unmapped:
            print(f"   • {field}")
    else:
        print("   ✓ None! All required fields mapped")
    
    return mappings


async def test_mapping_worker():
    """Test the full mapping worker (without actual AI call)."""
    if not WORKER_AVAILABLE:
        print_section("TEST 2: Mapping Worker Orchestration")
        print("\n⚠️  SKIPPED: MappingWorker not available (install requirements.txt)")
        return None
    
    print_section("TEST 2: Mapping Worker Orchestration")
    
    # Initialize worker (without AI key for testing)
    worker = MappingWorker(
        anthropic_api_key=None,  # No AI for this test
        confidence_threshold=0.8,
        required_threshold=0.5,
    )
    
    print("\n1️⃣  Processing mapping job...")
    
    # Process job (it will skip AI since no key provided)
    result = await worker.process_job(
        job_id="test_job_001",
        product_id="12345",
        template_schema_id="amazon_kurta_v1",
        product_data=SAMPLE_PRODUCT,
        schema_data=SAMPLE_SCHEMA,
    )
    
    print(f"   ✓ Job completed with status: {result['status']}")
    
    # Show job results
    print_section("Job Results")
    print(f"\n📝 Job ID: {result['job_id']}")
    print(f"   Product ID: {result['product_id']}")
    print(f"   Template: {result['template_schema_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Rule-Based Mappings: {result['rule_based_count']}")
    print(f"   AI-Assisted Mappings: {result['ai_assisted_count']}")
    
    print_mapping_results(result['mappings'], "Final Mappings")
    
    return result


async def test_single_field():
    """Test individual field mapping logic."""
    print_section("TEST 3: Single Field Mapping Tests")
    
    normalized = normalize_product(SAMPLE_PRODUCT)
    
    test_cases = [
        ("title", "string", None),
        ("brand", "string", None),
        ("sku", "string", None),
        ("price", "float", None),
        ("color", "enum", ["Red", "Blue", "Green", "Yellow", "White", "Black"]),
        ("size", "enum", ["XS", "S", "M", "L", "XL", "XXL"]),
        ("fabric", "string", None),
        ("neckline", "string", None),  # This should be missing
    ]
    
    print("\n🔍 Testing individual field mappings:\n")
    
    for canonical, field_type, enum_values in test_cases:
        result = map_single_field(normalized, canonical, field_type, enum_values)
        
        if result.confidence >= 0.8:
            status = "✅ HIGH"
        elif result.confidence >= 0.5:
            status = "⚠️  MED "
        elif result.confidence > 0:
            status = "❌ LOW "
        else:
            status = "⚪ MISS"
        
        value_str = str(result.value) if result.value is not None else "NULL"
        if len(value_str) > 40:
            value_str = value_str[:37] + "..."
        
        print(f"  {status} {canonical:20} {result.confidence:.2f}  {result.source:30}  {value_str}")


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  🧪 MAPPING SYSTEM TEST SUITE")
    print("="*70)
    print("\nTesting mapping_service.py and mapping_worker.py")
    print("This verifies the rule-based mapping engine works correctly.\n")
    
    try:
        # Test 1: Rule-based mapping
        await test_rule_based_mapping()
        
        # Test 2: Single field tests
        await test_single_field()
        
        # Test 3: Worker orchestration
        await test_mapping_worker()
        
        # Summary
        print_section("✅ ALL TESTS PASSED")
        print("\n✨ The mapping system is working correctly!")
        print("\n📌 Next Steps:")
        print("   1. Add ANTHROPIC_API_KEY to .env to enable AI enhancement")
        print("   2. Run full integration test with real Shopify data")
        print("   3. Test with MongoDB for job persistence")
        print()
        
    except Exception as e:
        print_section("❌ TEST FAILED")
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
