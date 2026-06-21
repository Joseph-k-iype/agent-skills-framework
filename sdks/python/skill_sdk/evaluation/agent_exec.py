from __future__ import annotations

from .sandbox import Workspace, build_tools
from .trajectory import RunResult, Trajectory


def _system_text(skill_body: str | None) -> str:
    if skill_body:
        return (
            "You are an agent completing a task by following the skill instructions below. "
            "Use the provided tools to do real work in the workspace.\n\n"
            "=== SKILL INSTRUCTIONS ===\n" + skill_body
        )
    return (
        "You are an agent completing a task. Use the provided tools to do real work "
        "in the workspace."
    )


def run_agent(
    prompt: str,
    ws: Workspace,
    model,
    *,
    skill_body: str | None = None,
    full_surface: bool = False,
    step_cap: int = 12,
) -> RunResult:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    traj = Trajectory()
    result = RunResult(workspace_path=str(ws.path), trajectory=traj)
    try:
        tools = build_tools(ws, traj, full_surface=full_surface)
        tools_by_name = {t.name: t for t in tools}
        bound = model.bind_tools(tools) if tools else model
        messages = [SystemMessage(_system_text(skill_body)), HumanMessage(prompt)]

        for _ in range(step_cap):
            ai: AIMessage = bound.invoke(messages)
            messages.append(ai)
            usage = getattr(ai, "usage_metadata", None) or {}
            traj.tokens_in += usage.get("input_tokens", 0)
            traj.tokens_out += usage.get("output_tokens", 0)
            tool_calls = getattr(ai, "tool_calls", None) or []
            if not tool_calls:
                result.final_text = ai.content if isinstance(ai.content, str) else str(ai.content)
                result.permission_violations = ws.violations
                return result
            for call in tool_calls:
                name = call["name"]
                tool = tools_by_name.get(name)
                if tool is None:
                    ws.violations.append(f"agent attempted undeclared capability '{name}'")
                    out = f"error: tool '{name}' not available (permission not declared)"
                else:
                    out = tool.invoke(call["args"])
                messages.append(ToolMessage(content=str(out), tool_call_id=call["id"]))

        result.error = f"step cap ({step_cap}) reached without completion"
        result.permission_violations = ws.violations
        return result
    except Exception as e:  # never let a run crash the suite
        result.error = f"{type(e).__name__}: {e}"
        result.permission_violations = ws.violations
        return result
