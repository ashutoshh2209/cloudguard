# Map security categories to broader high-level dashboard categories
CATEGORY_MAPPINGS = {
    "identity": "IDENTITY",
    "storage": "STORAGE",
    "network": "NETWORK",
    "compute": "COMPUTE",
    "database": "DATABASE",
    "logging": "MONITORING"
}

def map_category(raw_category: str) -> str:
    """Returns the mapped high-level category or 'OTHER' if unknown."""
    return CATEGORY_MAPPINGS.get(raw_category.lower(), "OTHER")
