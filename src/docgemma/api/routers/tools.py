"""Tools information endpoint."""

from fastapi import APIRouter

from ..models.responses import ToolInfo, ToolListResponse
from ...tools.registry import TOOL_REGISTRY

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    """List all available tools."""
    tools = []
    for name in TOOL_REGISTRY.names:
        tool_def = TOOL_REGISTRY.get(name)
        if tool_def:
            tools.append(
                ToolInfo(
                    name=tool_def.name,
                    description=tool_def.description,
                    args=tool_def.args,
                )
            )
    return ToolListResponse(tools=tools)


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool(tool_name: str) -> ToolInfo:
    """Get information about a specific tool."""
    tool_def = TOOL_REGISTRY.get(tool_name)
    if not tool_def:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return ToolInfo(
        name=tool_def.name,
        description=tool_def.description,
        args=tool_def.args,
    )
