from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain.agents import create_agent

from .tools import (
    make_read_reference_examples_tool,
    make_read_skill_md_tool,
    make_run_test_case_tool,
    make_score_rubric_tool,
)

CONTENT_CRITIC_SYSTEM_PROMPT = """You are a skill-documentation critic for an AI \
agent-skills framework. You review a single skill's manifest (SKILL.md) against the \
Anthropic Agent Skills standard.

Use read_skill_md to read the manifest, and read_reference_examples to see how other \
skills in this repo are documented. Then check specifically for:
1. Does the `description` field say WHEN an agent should invoke this skill (a \
   trigger/use-case clause), not just WHAT the skill does? This is the field a model \
   uses to decide whether to load the skill at all.
2. Does the Markdown body give real step-by-step procedural instructions, or does it \
   just restate the YAML frontmatter?
3. Any other clarity/completeness gaps that would confuse an agent trying to follow \
   this skill.

When you are done investigating, respond with ONLY a JSON object (no prose, no code \
fence) of the form:
{"findings": [{"id": "<short-slug>", "severity": "info"|"warning"|"error", \
"field": "<field name or 'body'>", "message": "<what's wrong>", \
"suggestion": "<concrete fix>", "signature": "<stable-lowercase-key>"}]}
If there are no issues, respond with {"findings": []}.
"""

TEST_EXECUTOR_SYSTEM_PROMPT = """You are a test-execution judge for an AI agent-skills \
framework. You are given a list of llm_judged eval cases, each with a rubric and the \
skill's raw output for that case. For each one, call score_rubric with a 0-100 score \
and a short rationale of how well the raw output satisfies the rubric.

When you are done scoring every case, respond with ONLY a JSON object (no prose, no \
code fence) of the form:
{"judgments": [{"case_id": "<id>", "score": <0-100>, "passed": <bool>, \
"rationale": "<why>"}]}
"""


def build_content_critic_agent(model, skill_path: str | Path, exclude_name: str | None = None,
                                memory_context: str = ""):
    tools = [
        make_read_skill_md_tool(skill_path),
        make_read_reference_examples_tool(exclude_name=exclude_name),
    ]
    prompt = CONTENT_CRITIC_SYSTEM_PROMPT
    if memory_context:
        prompt = f"{prompt}\n\n{memory_context}"
    return create_agent(model, tools, system_prompt=prompt)


def build_test_executor_agent(model, skill_path: str | Path):
    tools = [make_run_test_case_tool(skill_path), make_score_rubric_tool()]
    return create_agent(model, tools, system_prompt=TEST_EXECUTOR_SYSTEM_PROMPT)


def _last_ai_text(agent_result: dict[str, Any]) -> str:
    for msg in reversed(agent_result.get("messages", [])):
        is_ai = getattr(msg, "type", None) == "ai"
        if is_ai and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return ""


def _parse_json_list(text: str, key: str) -> list[dict[str, Any]]:
    """Best-effort parse of an agent's final JSON answer; tolerant of code fences
    and outright garbage — a parse failure just yields no findings/judgments
    rather than raising."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get(key, [])
    return data if isinstance(data, list) else []


def run_content_critic(model, skill_path: str | Path, exclude_name: str | None = None,
                        memory_context: str = "") -> list[dict[str, Any]]:
    agent = build_content_critic_agent(
        model, skill_path, exclude_name=exclude_name, memory_context=memory_context
    )
    result = agent.invoke({
        "messages": [(
            "user",
            "Review this skill's SKILL.md and report your findings as instructed.",
        )]
    })
    return _parse_json_list(_last_ai_text(result), "findings")


def run_test_executor(
    model, skill_path: str | Path, llm_judged_cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not llm_judged_cases:
        return []
    agent = build_test_executor_agent(model, skill_path)
    cases_desc = "\n".join(
        f"- case_id={c['case_id']} rubric={c.get('rubric')!r} raw_output={c.get('actual')!r}"
        for c in llm_judged_cases
    )
    message = (
        "Score each of the following llm_judged test cases, then respond as "
        "instructed:\n" + cases_desc
    )
    result = agent.invoke({"messages": [("user", message)]})
    return _parse_json_list(_last_ai_text(result), "judgments")
