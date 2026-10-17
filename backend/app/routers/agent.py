from __future__ import annotations
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AgentInstruction
from app.schemas.schemas import AgentInstructionRequest, AgentInstructionResponse
from app.services.agent_workspace import AgentWorkspaceService

router = APIRouter(prefix="/api/agent", tags=["AI Agent Workspace"])

@router.post("/instruct", response_model=AgentInstructionResponse)
def execute_instruction(payload: AgentInstructionRequest, db: Session = Depends(get_db)):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Instruction prompt cannot be empty.")
    
    result = AgentWorkspaceService.interpret_and_execute_instruction(payload.prompt, db)
    instruction = db.query(AgentInstruction).filter_by(id=result["instruction_id"]).first()
    return AgentInstructionResponse(
        id=instruction.id,
        objective=instruction.objective,
        extracted_filters=instruction.extracted_filters,
        search_plan=instruction.search_plan,
        status=instruction.status,
        leads_found=instruction.leads_found,
        applications_created=instruction.applications_created,
        created_at=instruction.created_at
    )

@router.get("/history", response_model=List[AgentInstructionResponse])
def get_instruction_history(db: Session = Depends(get_db)):
    instructions = db.query(AgentInstruction).order_by(AgentInstruction.id.desc()).limit(20).all()
    return [
        AgentInstructionResponse(
            id=i.id,
            objective=i.objective,
            extracted_filters=i.extracted_filters,
            search_plan=i.search_plan,
            status=i.status,
            leads_found=i.leads_found,
            applications_created=i.applications_created,
            created_at=i.created_at
        ) for i in instructions
    ]
