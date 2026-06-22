from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from skill_sdk.graph import FalkorDBConnector

from ..security import require_api_key, resolve_in_workspace

router = APIRouter()


class GraphConnectRequest(BaseModel):
    host: str = "localhost"
    port: int = 6379


class GraphRegisterRequest(BaseModel):
    host: str = "localhost"
    port: int = 6379
    manifest_path: str


class GraphQueryRequest(BaseModel):
    host: str = "localhost"
    port: int = 6379
    capability: str | None = None
    impact_id: str | None = None
    permission_resource: str | None = None


@router.post("/connect")
async def test_connection(req: GraphConnectRequest):
    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    try:
        connected = await graph.connect()
    except Exception:
        connected = False
    finally:
        graph.disconnect()
    return {"connected": bool(connected), "host": req.host, "port": req.port}


@router.post("/register", dependencies=[Depends(require_api_key)])
async def register_skill(req: GraphRegisterRequest):
    # Confine the manifest path to the workspace sandbox.
    manifest_path = resolve_in_workspace(req.manifest_path)
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest not found: {manifest_path}")
    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    connected = await graph.connect()
    if not connected:
        raise HTTPException(status_code=503, detail="Could not connect to FalkorDB")
    try:
        result = graph.register_skill(str(manifest_path))
        graph.disconnect()
        return result
    except Exception as e:
        graph.disconnect()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/query")
async def query_graph(req: GraphQueryRequest):
    if not (req.capability or req.impact_id or req.permission_resource):
        raise HTTPException(status_code=400, detail="Provide capability, impact_id, or permission_resource")

    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    try:
        connected = await graph.connect()
        if not connected:
            raise HTTPException(status_code=503, detail="Could not connect to FalkorDB")
        if req.capability:
            results = graph.find_skills_by_capability(req.capability)
        elif req.impact_id:
            results = graph.find_impact(req.impact_id)
        else:
            results = graph.find_skills_by_permission(req.permission_resource)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph query failed: {e}")
    finally:
        graph.disconnect()
