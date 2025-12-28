"""
Normalizer Worker

Normalizes product text and extracts attributes using heuristics.
Cleans up titles, descriptions, and extracts materials, colors, sizes.
"""
import re
from typing import Any, Dict, List, Optional, Set


# Common material/fabric patterns
MATERIAL_PATTERNS = [
    r"(\d+%?\s*(?:pure\s+)?(?:organic\s+)?cotton)",
    r"(\d+%?\s*(?:pure\s+)?silk)",
    r"(\d+%?\s*(?:pure\s+)?linen)",
    r"(\d+%?\s*(?:pure\s+)?wool)",
    r"(\d+%?\s*polyester)",
    r"(\d+%?\s*rayon)",
    r"(\d+%?\s*viscose)",
    r"(\d+%?\s*nylon)",
    r"(\d+%?\s*spandex)",
    r"(\d+%?\s*elastane)",
    r"(\d+%?\s*lycra)",
    r"(\d+%?\s*acrylic)",
    r"(\d+%?\s*modal)",
    r"(\d+%?\s*bamboo)",
    r"(\d+%?\s*hemp)",
    r"(\d+%?\s*cashmere)",
    r"(\d+%?\s*denim)",
    r"(\d+%?\s*velvet)",
    r"(\d+%?\s*satin)",
    r"(\d+%?\s*chiffon)",
    r"(\d+%?\s*georgette)",
    r"(\d+%?\s*crepe)",
    r"(khadi)",
    r"(chanderi)",
    r"(banarasi)",
    r"(jacquard)",
]

# Common color words mapping
COLOR_MAP: Dict[str, str] = {
    # Basic colors
    "red": "Red",
    "blue": "Blue",
    "green": "Green",
    "yellow": "Yellow",
    "orange": "Orange",
    "purple": "Purple",
    "pink": "Pink",
    "black": "Black",
    "white": "White",
    "grey": "Grey",
    "gray": "Grey",
    "brown": "Brown",
    "beige": "Beige",
    "cream": "Cream",
    "ivory": "Ivory",
    "gold": "Gold",
    "silver": "Silver",

    # Shades
    "navy": "Navy Blue",
    "navy blue": "Navy Blue",
    "sky blue": "Sky Blue",
    "royal blue": "Royal Blue",
    "turquoise": "Turquoise",
    "teal": "Teal",
    "aqua": "Aqua",
    "cyan": "Cyan",
    "indigo": "Indigo",
    "violet": "Violet",
    "lavender": "Lavender",
    "magenta": "Magenta",
    "maroon": "Maroon",
    "burgundy": "Burgundy",
    "coral": "Coral",
    "peach": "Peach",
    "rose": "Rose",
    "olive": "Olive",
    "lime": "Lime",
    "mint": "Mint",
    "forest green": "Forest Green",
    "emerald": "Emerald",
    "khaki": "Khaki",
    "tan": "Tan",
    "chocolate": "Chocolate",
    "rust": "Rust",
    "mustard": "Mustard",
    "charcoal": "Charcoal",

    # Multi-color indicators
    "multicolor": "Multicolor",
    "multi-color": "Multicolor",
    "multicolour": "Multicolor",
    "multi-colour": "Multicolor",
    "printed": "Printed",
}

# Common size patterns
SIZE_PATTERNS = [
    r"\b(XXS|XS|S|M|L|XL|XXL|XXXL|2XL|3XL|4XL|5XL)\b",
    r"\b(extra small|small|medium|large|extra large)\b",
    r"\b(\d{2})\b",  # Numeric sizes like 32, 34, 36, etc.
    r"\bsize\s*[-:]?\s*(\w+)\b",
    r"\b(free size|one size|free)\b",
]

# Neckline patterns
NECKLINE_PATTERNS = {
    r"\bmandarin\s+collar\b": "Mandarin Collar",
    r"\bmandarin\b": "Mandarin Collar",
    r"\bv[-\s]?neck\b": "V-Neck",
    r"\bv\s+neck\b": "V-Neck",
    r"\bround\s+neck\b": "Round Neck",
    r"\bcrew\s+neck\b": "Crew Neck",
    r"\bboat\s+neck\b": "Boat Neck",
    r"\bturtleneck\b": "Turtleneck",
    r"\bturtle\s+neck\b": "Turtleneck",
    r"\bhigh\s+neck\b": "High Neck",
    r"\bcowl\s+neck\b": "Cowl Neck",
    r"\bhalter\s+neck\b": "Halter Neck",
    r"\boff[-\s]?shoulder\b": "Off Shoulder",
    r"\bsquare\s+neck\b": "Square Neck",
    r"\bscoop\s+neck\b": "Scoop Neck",
    r"\bsweetheart\s+neck\b": "Sweetheart Neck",
    r"\bcollar\s+neck\b": "Collar Neck",
    r"\bchineese\s+collar\b": "Chinese Collar",
    r"\bchinese\s+collar\b": "Chinese Collar",
    r"\bnotch\s+collar\b": "Notch Collar",
    r"\bshawl\s+collar\b": "Shawl Collar",
}


def clean_text(text: Optional[str]) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Convert to string if needed
    text = str(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove HTML entities
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)

    # Remove special characters but keep basic punctuation
    text = re.sub(r"[^\w\s.,;:!?'\"-]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def clean_title(title: Optional[str]) -> str:
    """
    Clean and normalize product title.

    Args:
        title: Raw product title

    Returns:
        Cleaned title
    """
    if not title:
        return ""

    cleaned = clean_text(title)

    # Remove common prefixes/suffixes that don't add value
    patterns_to_remove = [
        r"^buy\s+",
        r"^shop\s+",
        r"\s+online\s*$",
        r"\s+for\s+(men|women|boys|girls|kids)\s*$",
    ]

    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def clean_description(description: Optional[str]) -> str:
    """
    Clean and normalize product description.

    Args:
        description: Raw product description

    Returns:
        Cleaned description
    """
    if not description:
        return ""

    cleaned = clean_text(description)

    # Remove excessive marketing language
    marketing_phrases = [
        r"buy now",
        r"order now",
        r"limited time offer",
        r"best seller",
        r"hurry up",
        r"don't miss",
    ]

    for phrase in marketing_phrases:
        cleaned = re.sub(phrase, "", cleaned, flags=re.IGNORECASE)

    # Limit to reasonable length
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000] + "..."

    return cleaned.strip()


def extract_materials(text: str) -> List[str]:
    """
    Extract material/fabric information from text.

    Args:
        text: Text to search for materials

    Returns:
        List of extracted material strings
    """
    if not text:
        return []

    text_lower = text.lower()
    materials: Set[str] = set()

    for pattern in MATERIAL_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip()
            if cleaned:
                # Capitalize properly
                materials.add(cleaned.title())

    return sorted(list(materials))


def extract_colors(text: str) -> List[str]:
    """
    Extract color information from text.

    Args:
        text: Text to search for colors

    Returns:
        List of extracted color names
    """
    if not text:
        return []

    text_lower = text.lower()
    colors: Set[str] = set()

    # Check for color words
    for color_key, color_name in COLOR_MAP.items():
        # Use word boundary matching
        pattern = r"\b" + re.escape(color_key) + r"\b"
        if re.search(pattern, text_lower):
            colors.add(color_name)

    return sorted(list(colors))


def extract_sizes(text: str) -> List[str]:
    """
    Extract size information from text.

    Args:
        text: Text to search for sizes

    Returns:
        List of extracted sizes
    """
    if not text:
        return []

    sizes: Set[str] = set()

    for pattern in SIZE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip().upper()
            # Filter out unlikely matches (years, prices, etc.)
            if cleaned in ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "2XL", "3XL", "4XL", "5XL"]:
                sizes.add(cleaned)
            elif cleaned.lower() in ["free size", "one size", "free"]:
                sizes.add("Free Size")
            elif cleaned.isdigit() and 28 <= int(cleaned) <= 60:
                sizes.add(cleaned)

    return sorted(list(sizes))


def extract_neckline(text: str) -> Optional[str]:
    """
    Extract neckline/collar type from text.

    Args:
        text: Text to extract from (title, description, etc.)

    Returns:
        Extracted neckline type or None
    """
    if not text:
        return None

    text_lower = text.lower()

    # Try to match neckline patterns
    for pattern, neckline_type in NECKLINE_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            return neckline_type

    return None


def simplify_variants(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simplify variant data to essential fields.

    Args:
        variants: Raw variant data from Shopify

    Returns:
        Simplified variant list
    """
    if not variants:
        return []

    simplified = []

    for variant in variants:
        simplified_variant = {
            "id": str(variant.get("id", "")),
            "sku": variant.get("sku", ""),
            "title": variant.get("title", ""),
            "price": variant.get("price", ""),
            "compare_at_price": variant.get("compare_at_price"),
            "inventory_quantity": variant.get("inventory_quantity", 0),
        }

        # Extract option values
        for i in range(1, 4):
            option_key = f"option{i}"
            if option_key in variant and variant[option_key]:
                simplified_variant[option_key] = variant[option_key]

        # Extract weight if present
        if variant.get("weight"):
            simplified_variant["weight"] = variant["weight"]
            simplified_variant["weight_unit"] = variant.get("weight_unit", "g")

        simplified.append(simplified_variant)

    return simplified


def normalize_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a product JSON to extract clean data and attributes.

    Args:
        product: Raw product data (typically from Shopify)

    Returns:
        Normalized product with extracted attributes
    """
    title = product.get("title", "")
    # Shopify uses body_html, but also accept description
    description = product.get("body_html", product.get("description", ""))

    # Combine all text for material/color/neckline extraction
    all_text = f"{title} {description}"

    # Add metafield text if present
    metafields = product.get("metafields", {})
    if isinstance(metafields, dict):
        custom_fields = metafields.get("custom", {})
        if isinstance(custom_fields, dict):
            for key, value in custom_fields.items():
                if isinstance(value, str):
                    all_text += f" {value}"

    # Add variant text
    variants = product.get("variants", [])
    for variant in variants:
        for i in range(1, 4):
            option = variant.get(f"option{i}")
            if option:
                all_text += f" {option}"

    # Build normalized result
    normalized = {
        "original_id": str(product.get("id", "")),
        "cleaned_title": clean_title(title),
        "cleaned_description": clean_description(description),
        "extracted_materials": extract_materials(all_text),
        "extracted_colors": extract_colors(all_text),
        "extracted_neckline": extract_neckline(all_text),
        "sizes": extract_sizes(all_text),
        "variants_simplified": simplify_variants(variants),

        # Preserve some original fields
        "vendor": product.get("vendor", ""),
        "product_type": product.get("product_type", ""),
        "tags": product.get("tags", []),
        "metafields": metafields,
    }

    # Extract image URLs
    images = product.get("images", [])
    if images:
        normalized["main_image_url"] = images[0].get("src", "") if images else ""
        normalized["other_image_urls"] = [
            img.get("src", "") for img in images[1:] if img.get("src")
        ]
    else:
        normalized["main_image_url"] = ""
        normalized["other_image_urls"] = []

    return normalized


def normalize_batch(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize a batch of products.

    Args:
        products: List of raw product data

    Returns:
        List of normalized products
    """
    return [normalize_product(product) for product in products]
