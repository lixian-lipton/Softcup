from fastapi import APIRouter

from app.schemas import WorkflowRequest, WorkflowResponse
from app.services.workflow import build_workflow

router = APIRouter(prefix="/api", tags=["作业指引"])


@router.post("/workflow", response_model=WorkflowResponse)
async def workflow(req: WorkflowRequest):
    return await build_workflow(
        device_model=req.device_model,
        maintenance_level=req.maintenance_level,
        fault_description=req.fault_description,
    )
