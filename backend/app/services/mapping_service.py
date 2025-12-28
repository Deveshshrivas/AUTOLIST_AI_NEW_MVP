"""
Rule-Based Mapping Service

Deterministic mapper that maps Shopify product keys to canonical schema fields.
Uses exact key matching, metafield mapping, synonym dictionaries, and enum normalization.
"""
from typing import Any, Dict, List, Optional, Tuple
import re


# Synonym dictionary for field name mapping
FIELD_SYNONYMS: Dict[str, List[str]] = {
    "sku": ["sku", "item_sku", "seller_sku", "product_sku", "article_number"],
    "parent_sku": ["parent_sku", "parent_child", "group_id", "parent_id"],
    "title": ["title", "name", "product_name", "item_name", "product_title"],
    "description": ["description", "body_html", "product_description", "long_description"],
    "brand": ["brand", "vendor", "brand_name", "manufacturer"],
    "price": ["price", "standard_price", "list_price", "variant_price"],
    "sale_price": ["sale_price", "compare_at_price", "discount_price"],
    "color": ["color", "colour", "color_name", "colour_name"],
    "size": ["size", "size_name", "item_size", "product_size"],
    "fabric": ["fabric", "fabric_type", "material", "material_type", "fabric_composition"],
    "weight": ["weight", "item_weight", "product_weight"],
    "main_image_url": ["main_image_url", "image_src", "featured_image", "image_url"],
    "quantity": ["quantity", "inventory_quantity", "stock", "stock_quantity"],
    "product_type": ["product_type", "category", "item_type", "type"],
}

# Reverse lookup: from any synonym to canonical field
SYNONYM_TO_CANONICAL: Dict[str, str] = {}
for canonical, synonyms in FIELD_SYNONYMS.items():
    for syn in synonyms:
        SYNONYM_TO_CANONICAL[syn.lower()] = canonical


class MappingResult:
    """Result of mapping a single field."""

    def __init__(
        self,
        value: Optional[Any],
        source: str,
        confidence: float,
    ):
        self.value = value
        self.source = source
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
        }


def normalize_key(key: str) -> str:
    """Normalize a key for comparison."""
    return key.lower().strip().replace("-", "_").replace(" ", "_")


def get_nested_value(data: Dict, path: str) -> Optional[Any]:
    """
    Get a value from nested dictionary using dot notation.

    Args:
        data: Dictionary to search
        path: Dot-separated path (e.g., "metafields.custom.fabric")

    Returns:
        Value at path or None
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if isinstance(current, dict):
            # Try exact key first, then normalized
            if key in current:
                current = current[key]
            elif normalize_key(key) in {normalize_key(k): v for k, v in current.items()}:
                # Find the actual key
                for k, v in current.items():
                    if normalize_key(k) == normalize_key(key):
                        current = v
                        break
            else:
                return None
        else:
            return None

    return current


def match_enum_value(value: Any, enum_values: List[str]) -> Tuple[Optional[str], float]:
    """
    Match a value to an enum list (case-insensitive).

    Args:
        value: Value to match
        enum_values: List of valid enum values

    Returns:
        Tuple of (matched_value, confidence)
    """
    if value is None:
        return None, 0.0

    value_str = str(value).strip().lower()

    # Exact match (case-insensitive)
    for enum_val in enum_values:
        if enum_val.lower() == value_str:
            return enum_val, 0.95

    # Partial match (value contains or is contained by enum)
    for enum_val in enum_values:
        enum_lower = enum_val.lower()
        if value_str in enum_lower or enum_lower in value_str:
            return enum_val, 0.85

    # Fuzzy match for common variations
    value_normalized = re.sub(r"[^a-z0-9]", "", value_str)
    for enum_val in enum_values:
        enum_normalized = re.sub(r"[^a-z0-9]", "", enum_val.lower())
        if value_normalized == enum_normalized:
            return enum_val, 0.80

    return None, 0.0


def extract_from_variants(
    variants: List[Dict],
    canonical_field: str,
) -> Tuple[Optional[Any], str, float]:
    """
    Extract a value from variant data.

    Args:
        variants: List of variant dictionaries
        canonical_field: The canonical field to extract

    Returns:
        Tuple of (value, source, confidence)
    """
    if not variants:
        return None, "", 0.0

    first_variant = variants[0]

    # Direct variant fields
    if canonical_field == "sku":
        if first_variant.get("sku"):
            return first_variant["sku"], "variant.sku", 0.95

    if canonical_field == "price":
        if first_variant.get("price"):
            return first_variant["price"], "variant.price", 0.95

    if canonical_field == "sale_price":
        if first_variant.get("compare_at_price"):
            return first_variant["compare_at_price"], "variant.compare_at_price", 0.95

    if canonical_field == "quantity":
        if "inventory_quantity" in first_variant:
            return first_variant["inventory_quantity"], "variant.inventory_quantity", 0.95

    if canonical_field == "weight":
        if first_variant.get("weight"):
            weight = first_variant["weight"]
            unit = first_variant.get("weight_unit", "g")
            return f"{weight} {unit}", "variant.weight", 0.90

    # Check option fields for size/color
    if canonical_field in ["size", "color"]:
        for i in range(1, 4):
            option_key = f"option{i}"
            if option_key in first_variant:
                option_value = first_variant[option_key]
                # Heuristic: if it looks like a size
                if canonical_field == "size":
                    size_patterns = ["xs", "s", "m", "l", "xl", "xxl", "xxxl", "free"]
                    if any(p in str(option_value).lower() for p in size_patterns):
                        return option_value, f"variant.{option_key}", 0.85
                    if str(option_value).isdigit() and 28 <= int(option_value) <= 60:
                        return option_value, f"variant.{option_key}", 0.85

                # Heuristic: if it looks like a color
                if canonical_field == "color":
                    from ..workers.normalizer import COLOR_MAP
                    if str(option_value).lower() in COLOR_MAP:
                        return option_value, f"variant.{option_key}", 0.85

    return None, "", 0.0


def map_to_schema(
    product: Dict[str, Any],
    schema: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Map a product to a canonical schema.

    Args:
        product: Normalized product data
        schema: Template schema with columns definition

    Returns:
        Mapping dictionary: {canonical_field: {value, source, confidence}}
    """
    mappings: Dict[str, Dict[str, Any]] = {}
    columns = schema.get("columns", [])

    for column in columns:
        canonical = column["canonical"]
        field_type = column.get("type", "string")
        enum_values = column.get("enum")

        result = map_single_field(product, canonical, field_type, enum_values)
        mappings[canonical] = result.to_dict()

    return mappings


def map_single_field(
    product: Dict[str, Any],
    canonical_field: str,
    field_type: str = "string",
    enum_values: Optional[List[str]] = None,
) -> MappingResult:
    """
    Map a single canonical field from product data.

    Strategy:
    1. Exact key mapping from product
    2. Metafield mapping
    3. Synonym dictionary mapping
    4. Variant extraction
    5. Extracted attributes (from normalizer)
    6. Enum normalization if applicable

    Args:
        product: Product data dictionary
        canonical_field: Target canonical field name
        field_type: Expected data type
        enum_values: Valid enum values if applicable

    Returns:
        MappingResult with value, source, and confidence
    """
    value = None
    source = ""
    confidence = 0.0

    # 1. Exact key mapping
    if canonical_field in product:
        value = product[canonical_field]
        source = f"product.{canonical_field}"
        confidence = 0.95

    # 2. Try cleaned versions from normalizer
    if value is None:
        cleaned_key = f"cleaned_{canonical_field}"
        if cleaned_key in product:
            value = product[cleaned_key]
            source = f"product.{cleaned_key}"
            confidence = 0.95

    # 3. Metafield mapping
    if value is None:
        metafields = product.get("metafields", {})
        if isinstance(metafields, dict):
            custom = metafields.get("custom", {})
            if isinstance(custom, dict):
                # Try exact canonical field
                if canonical_field in custom:
                    value = custom[canonical_field]
                    source = f"metafield.custom.{canonical_field}"
                    confidence = 0.95

                # Try synonyms in metafields
                if value is None:
                    synonyms = FIELD_SYNONYMS.get(canonical_field, [])
                    for syn in synonyms:
                        if syn in custom:
                            value = custom[syn]
                            source = f"metafield.custom.{syn}"
                            confidence = 0.90
                            break
                
                # Special case: fabric from material_type or fabric_type
                if value is None and canonical_field == "fabric":
                    for key in ["material_type", "fabric_type", "material", "fabric_composition"]:
                        if key in custom:
                            value = custom[key]
                            source = f"metafield.custom.{key}"
                            confidence = 0.90
                            break

    # 4. Synonym dictionary mapping
    if value is None:
        synonyms = FIELD_SYNONYMS.get(canonical_field, [])
        for syn in synonyms:
            if syn in product:
                value = product[syn]
                source = f"product.{syn}"
                confidence = 0.90
                break

    # 5. Variant extraction
    if value is None:
        variants = product.get("variants_simplified", product.get("variants", []))
        if variants:
            var_value, var_source, var_conf = extract_from_variants(variants, canonical_field)
            if var_value is not None:
                value = var_value
                source = var_source
                confidence = var_conf

    # 6. Extracted attributes (from normalizer)
    if value is None:
        # Check extracted_* fields
        if canonical_field == "fabric" or canonical_field == "material":
            materials = product.get("extracted_materials", [])
            if materials:
                value = ", ".join(materials)
                source = "extracted.materials"
                confidence = 0.75
            else:
                # Try to extract from title or description
                title = product.get("cleaned_title", "")
                description = product.get("cleaned_description", "")
                combined_text = f"{title} {description}".lower()
                
                # Common fabric keywords in product titles/descriptions
                fabric_keywords = {
                    "cotton": "Cotton",
                    "polyester": "Polyester",
                    "silk": "Silk",
                    "linen": "Linen",
                    "wool": "Wool",
                    "denim": "Denim",
                    "leather": "Leather",
                    "rayon": "Rayon",
                    "nylon": "Nylon",
                    "spandex": "Spandex",
                }
                
                for keyword, fabric_name in fabric_keywords.items():
                    if keyword in combined_text:
                        value = fabric_name
                        source = "inferred.fabric"
                        confidence = 0.70
                        break

        elif canonical_field == "color":
            colors = product.get("extracted_colors", [])
            if colors:
                value = colors[0] if len(colors) == 1 else ", ".join(colors)
                source = "extracted.colors"
                confidence = 0.60

        elif canonical_field == "size":
            sizes = product.get("sizes", [])
            if sizes:
                value = sizes[0] if len(sizes) == 1 else ", ".join(sizes)
                source = "extracted.sizes"
                confidence = 0.60
        
        elif canonical_field == "neckline":
            neckline = product.get("extracted_neckline")
            if neckline:
                value = neckline
                source = "extracted.neckline"
                confidence = 0.90
        
        elif canonical_field == "parent_sku":
            # Try to generate parent SKU from variant SKU
            variants = product.get("variants_simplified", product.get("variants", []))
            if variants and variants[0].get("sku"):
                sku = variants[0]["sku"]
                # Extract parent from patterns like "K001-M-BLUE" -> "K001"
                # or "SHIRT_RED_L" -> "SHIRT"
                import re
                # Try common patterns
                patterns = [
                    r"^([A-Z0-9]+)[-_]",  # K001-M-BLUE -> K001
                    r"^([A-Z]+\d+)",       # K001MBLUE -> K001
                ]
                for pattern in patterns:
                    match = re.match(pattern, str(sku).upper())
                    if match:
                        value = match.group(1)
                        source = "generated.parent_sku"
                        confidence = 0.85
                        break
        
        elif canonical_field == "neckline":
            neckline = product.get("extracted_neckline")
            if neckline:
                value = neckline
                source = "extracted.neckline"
                confidence = 0.90
        
        elif canonical_field == "parent_sku":
            # Try to generate parent SKU from variant SKU
            variants = product.get("variants_simplified", product.get("variants", []))
            if variants and variants[0].get("sku"):
                sku = variants[0]["sku"]
                # Extract parent from patterns like "K001-M-BLUE" -> "K001"
                # or "SHIRT_RED_L" -> "SHIRT"
                import re
                # Try common patterns
                patterns = [
                    r"^([A-Z0-9]+)[-_]",  # K001-M-BLUE -> K001
                    r"^([A-Z]+\d+)",       # K001MBLUE -> K001
                ]
                for pattern in patterns:
                    match = re.match(pattern, str(sku).upper())
                    if match:
                        value = match.group(1)
                        source = "generated.parent_sku"
                        confidence = 0.85
                        break

    # 7. Image URL mapping
    if value is None and canonical_field == "main_image_url":
        if "main_image_url" in product:
            value = product["main_image_url"]
            source = "product.main_image_url"
            confidence = 0.95
        elif "images" in product and product["images"]:
            value = product["images"][0].get("src", "")
            source = "product.images[0].src"
            confidence = 0.90

    # 8. Enum normalization
    if value is not None and enum_values:
        matched_value, enum_confidence = match_enum_value(value, enum_values)
        if matched_value:
            value = matched_value
            confidence = min(confidence, enum_confidence)
        else:
            # Value doesn't match enum - flag it
            confidence = max(0.3, confidence - 0.3)

    # Create result
    if value is None:
        return MappingResult(None, "not_found", 0.0)

    return MappingResult(value, source, confidence)


def get_unmapped_fields(
    mappings: Dict[str, Dict[str, Any]],
    schema: Dict[str, Any],
    confidence_threshold: float = 0.8,
) -> List[str]:
    """
    Get list of fields that need AI assistance.

    Args:
        mappings: Current mapping results
        schema: Template schema
        confidence_threshold: Minimum confidence to consider mapped

    Returns:
        List of canonical field names needing AI mapping
    """
    unmapped = []
    columns = schema.get("columns", [])

    for column in columns:
        canonical = column["canonical"]
        mapping = mappings.get(canonical, {})

        value = mapping.get("value")
        confidence = mapping.get("confidence", 0.0)

        if value is None or confidence < confidence_threshold:
            unmapped.append(canonical)

    return unmapped


def get_required_unmapped(
    mappings: Dict[str, Dict[str, Any]],
    schema: Dict[str, Any],
    confidence_threshold: float = 0.5,
) -> List[str]:
    """
    Get list of REQUIRED fields that are unmapped or low confidence.

    Args:
        mappings: Current mapping results
        schema: Template schema
        confidence_threshold: Minimum confidence

    Returns:
        List of required field names with issues
    """
    required_unmapped = []
    columns = schema.get("columns", [])

    for column in columns:
        if not column.get("required", False):
            continue

        canonical = column["canonical"]
        mapping = mappings.get(canonical, {})

        value = mapping.get("value")
        confidence = mapping.get("confidence", 0.0)

        if value is None or confidence < confidence_threshold:
            required_unmapped.append(canonical)

    return required_unmapped
