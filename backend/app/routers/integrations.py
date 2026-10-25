from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IntegrationCredentialsMetadata
from app.schemas.schemas import IntegrationMetadataResponse, TestIntegrationRequest, ToggleIntegrationRequest, ConfigureIntegrationRequest
from app.services.integrations import IntegrationManager

router = APIRouter(prefix="/api/integrations", tags=["Integration Marketplace"])

@router.get("", response_model=List[IntegrationMetadataResponse])
def list_integrations(db: Session = Depends(get_db)):
    items = db.query(IntegrationCredentialsMetadata).all()
    return [
        IntegrationMetadataResponse(
            id=i.id,
            provider_name=i.provider_name,
            category=i.category,
            is_configured=i.is_configured,
            is_active=i.is_active,
            masked_key_hint=i.masked_key_hint or "",
            supported_capabilities=i.supported_capabilities or [],
            permissions_granted=i.permissions_granted or [],
            last_successful_operation=i.last_successful_operation,
            last_error=i.last_error or ""
        ) for i in items
    ]

@router.post("/test")
def test_integration(payload: TestIntegrationRequest, db: Session = Depends(get_db)):
    res = IntegrationManager.test_connection(payload.provider_name, payload.config, db)
    return res

@router.post("/toggle")
def toggle_integration(payload: ToggleIntegrationRequest, db: Session = Depends(get_db)):
    res = IntegrationManager.toggle_integration(payload.provider_name, payload.enable, db)
    return res

@router.post("/configure")
def configure_integration(payload: ConfigureIntegrationRequest, db: Session = Depends(get_db)):
    res = IntegrationManager.configure_integration(payload.provider_name, payload.api_key, payload.config, db)
    return res
