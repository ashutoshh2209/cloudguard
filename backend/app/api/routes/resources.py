from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.resource import resource_repo
# Assuming we don't have a specific Pydantic schema for CloudResource output yet, we can return generic dicts or define one.

router = APIRouter()

@router.get("/")
async def list_resources(
    scan_id: str = Query(..., description="Filter by scan ID"),
    skip: int = Query(0, description="Pagination skip"),
    limit: int = Query(50, description="Pagination limit"),
    db: Session = Depends(get_db)
):
    """
    Returns a list of resources for a given scan.
    """
    resources = resource_repo.get_by_scan(db, scan_id=scan_id, skip=skip, limit=limit)
    return resources
