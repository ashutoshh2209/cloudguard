from typing import Any, Optional, Dict
from app.models.resource import CloudResource

def extract_resource_metadata(resource: Any, context: Optional[dict] = None) -> Dict[str, Any]:
    """
    Extracts configuration metadata from either a CloudResource, inventory object, or dictionary.
    Safely merges with optional context without inventing evidence.
    """
    meta: Dict[str, Any] = {}
    if isinstance(resource, CloudResource):
        if resource.metadata_json and isinstance(resource.metadata_json, dict):
            meta.update(resource.metadata_json)
        meta.setdefault("resource_id", resource.resource_id)
        meta.setdefault("resource_name", resource.resource_name or resource.name)
        meta.setdefault("arn", resource.arn)
        meta.setdefault("region", resource.region)
        meta.setdefault("status", resource.status)
    elif isinstance(resource, dict):
        if "metadata" in resource and isinstance(resource["metadata"], dict):
            meta.update(resource["metadata"])
        elif "metadata_json" in resource and isinstance(resource["metadata_json"], dict):
            meta.update(resource["metadata_json"])
        else:
            meta.update(resource)
    elif hasattr(resource, "__dict__"):
        for k, v in resource.__dict__.items():
            if not k.startswith("_"):
                meta[k] = v

    if context and isinstance(context, dict):
        meta.update(context)

    return meta
