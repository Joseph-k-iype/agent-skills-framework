from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeToolCallingChatModel(BaseChatModel):
    """Minimal BaseChatModel double that supports bind_tools (unlike every
    fake chat model langchain-core ships — FakeListChatModel/GenericFakeChatModel/
    etc. all inherit BaseChatModel.bind_tools, which raises NotImplementedError).
    create_react_agent always calls bind_tools internally, so none of those
    work here; this is the prerequisite for testing any ReAct-agent code
    without a real network call.

    Construct with a queue of AIMessages (optionally carrying tool_calls) —
    each invoke() pops the next one in sequence.
    """

    responses: list[AIMessage] = []
    i: int = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:
        response = self.responses[self.i]
        self.i += 1
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling-chat-model"
