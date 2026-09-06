from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.resource import CloudResource

class ResourceRepository:
    def bulk_create(self, db: Session, scan_id: str, aws_connection_id: str, resources_data: List[Dict[str, Any]]):
        resources = []
        for r_data in resources_data:
            res = CloudResource(
                scan_id=scan_id,
                aws_connection_id=aws_connection_id,
                resource_id=r_data["resource_id"],
                resource_type=r_data["resource_type"],
                service=r_data["service"],
                name=r_data.get("name"),
                region=r_data["region"],
                metadata_json=r_data.get("metadata", {})
            )
            resources.append(res)
        if resources:
            db.bulk_save_objects(resources)
            db.flush()

    def get_by_scan(self, db: Session, scan_id: str, skip: int = 0, limit: int = 50) -> List[CloudResource]:
        return db.query(CloudResource).filter(CloudResource.scan_id == scan_id).offset(skip).limit(limit).all()

resource_repo = ResourceRepository()
