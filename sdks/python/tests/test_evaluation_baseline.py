import json
import tempfile
from pathlib import Path

from _fake_chat_model import FakeToolCallingChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from skill_sdk.evaluation.baseline import find_previous_version, run_agent_execution

MANIFEST = {"name": "demo", "version": "1.1.0",
            "permissions": [{"resource": "ws", "actions": ["read", "write", "create", "list"]}]}


class ContentInspectingChatModel(BaseChatModel):
    """Fake chat model that genuinely exercises the with/without fairness rule.

    Unlike a canned response queue, this model inspects whether the SKILL
    instructions text is present in the incoming messages: if present (the
    with-skill run), it returns a tool call that writes the asserted file
    (pass); if absent (the baseline run, skill_body=""), it returns a plain
    text response with no tool call, so the file is never created (fail).
    """

    needle: str = ""

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        text = "\n".join(
            m.content if isinstance(m.content, str) else str(m.content) for m in messages
        )
        if self.needle and self.needle in text:
            response = AIMessage(content="", tool_calls=[
                {"name": "write_file", "args": {"path": "out.txt", "content": "x"}, "id": "1"}])
        else:
            response = AIMessage(content="I don't know what to do.")
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "content-inspecting-fake-chat-model"


def _skill(tmp: Path, body: str = "Write out.txt with the answer.") -> Path:
    (tmp / "SKILL.md").write_text(f"---\nname: demo\nversion: 1.1.0\n---\n{body}")
    return tmp


def test_find_previous_version_picks_semver_max_below_current():
    reg = Path(tempfile.mkdtemp())
    skills = reg / "skills"
    for v in ("0.9.0", "1.0.0", "1.0.5", "1.1.0"):
        (skills / f"demo-{v}").mkdir(parents=True)
    prev = find_previous_version(reg, "demo", "1.1.0")
    assert prev is not None and prev.name == "demo-1.0.5"


def test_run_agent_execution_with_without_computes_delta():
    skill = _skill(Path(tempfile.mkdtemp()))
    reg = Path(tempfile.mkdtemp())  # no prior version -> with_without
    case = {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
            "expect": {"mode": "assertions",
                       "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}

    # with-skill writes the file (passes); baseline does nothing (fails)
    def fresh_model():
        return FakeToolCallingChatModel(responses=[
            AIMessage(content="", tool_calls=[
                {"name": "write_file", "args": {"path": "out.txt", "content": "x"}, "id": "1"}]),
            AIMessage(content="done"),
            AIMessage(content="I won't do it"),  # baseline run: no tool call
        ])

    summary = run_agent_execution(skill, MANIFEST, reg, [case], fresh_model())
    assert summary.comparison_mode == "with_without"
    assert summary.with_skill.pass_rate_mean == 1.0
    assert summary.baseline.pass_rate_mean == 0.0
    assert summary.delta["pass_rate"] == 1.0


def test_run_agent_execution_with_without_fairness_is_real():
    """Genuinely exercises the fairness rule: the fake model's behavior is
    driven by whether the SKILL instructions text is actually present in the
    messages it receives, not by a hard-coded response sequence. This means
    the test depends on the baseline branch really passing skill_body="" and
    full_surface=True — if that wiring were broken (e.g. the baseline run
    accidentally received the skill body), the model would emit the
    write_file tool call for the baseline run too, and the assertions below
    would fail.
    """
    needle = "Write out.txt with the answer."
    skill = _skill(Path(tempfile.mkdtemp()), body=needle)
    reg = Path(tempfile.mkdtemp())  # no prior version -> with_without
    case = {"id": "c1", "input": {"type": "task", "prompt": "produce out.txt"},
            "expect": {"mode": "assertions",
                       "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}

    model = ContentInspectingChatModel(needle=needle)
    summary = run_agent_execution(skill, MANIFEST, reg, [case], model)

    assert summary.comparison_mode == "with_without"
    assert summary.with_skill.pass_rate_mean == 1.0
    assert summary.baseline.pass_rate_mean == 0.0
    assert summary.delta["pass_rate"] == 1.0


def test_run_agent_execution_honors_per_case_baseline_override():
    """A prior version exists (which would auto-select vs_previous), but the
    case explicitly sets baseline: "with_without", which must win.
    """
    skill = _skill(Path(tempfile.mkdtemp()))
    reg = Path(tempfile.mkdtemp())
    skills = reg / "skills"
    (skills / "demo-1.0.0").mkdir(parents=True)
    (skills / "demo-1.0.0" / "SKILL.md").write_text(
        "---\nname: demo\nversion: 1.0.0\n---\nOld instructions."
    )
    case = {"id": "c1", "baseline": "with_without",
            "input": {"type": "task", "prompt": "produce out.txt"},
            "expect": {"mode": "assertions",
                       "assertions": [{"kind": "file_exists", "path": "out.txt"}]}}

    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "write_file", "args": {"path": "out.txt", "content": "x"}, "id": "1"}]),
        AIMessage(content="done"),
        AIMessage(content="I won't do it"),
    ])

    summary = run_agent_execution(skill, MANIFEST, reg, [case], model)
    assert summary.comparison_mode == "with_without"


def test_judge_run_parses_rubric_and_llm_assertions():
    from skill_sdk.evaluation.baseline import judge_run
    from skill_sdk.evaluation.trajectory import RunResult
    model = FakeToolCallingChatModel(responses=[AIMessage(content=json.dumps({
        "llm_assertions": [{"statement": "clean", "passed": True, "evidence": "tidy"}],
        "rubric_score": 80,
    }))])
    case = {"expect": {"assertions": [{"kind": "llm", "statement": "clean"}],
                       "rubric": "is it clean?"}}
    out = judge_run(model, case, RunResult(final_text="ok"))
    assert out["rubric_score"] == 80
    assert out["llm_assertions"][0]["passed"] is True
