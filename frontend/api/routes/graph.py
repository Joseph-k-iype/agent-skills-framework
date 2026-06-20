from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from skill_sdk.graph import FalkorDBConnector

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


@router.post("/connect")
async def test_connection(req: GraphConnectRequest):
    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    connected = await graph.connect()
    if connected:
        graph.disconnect()
        return {"connected": True, "host": req.host, "port": req.port}
    return {"connected": False, "host": req.host, "port": req.port}


@router.post("/register")
async def register_skill(req: GraphRegisterRequest):
    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    connected = await graph.connect()
    if not connected:
        raise HTTPException(status_code=503, detail="Could not connect to FalkorDB")
    try:
        result = graph.register_skill(req.manifest_path)
        graph.disconnect()
        return result
    except Exception as e:
        graph.disconnect()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/query")
async def query_graph(req: GraphQueryRequest):
    graph = FalkorDBConnector(host=req.host, port=req.port, enabled=True)
    connected = await graph.connect()
    if not connected:
        raise HTTPException(status_code=503, detail="Could not connect to FalkorDB")

    results = []
    if req.capability:
        results = graph.find_skills_by_capability(req.capability)
    elif req.impact_id:
        results = graph.find_impact(req.impact_id)
    else:
        graph.disconnect()
        raise HTTPException(status_code=400, detail="Provide capability or impact_id")

    graph.disconnect()
    return {"results": results}
