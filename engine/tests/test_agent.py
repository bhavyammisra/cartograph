"""The agent loop with a scripted fake LLM: no model, no database."""

import json
from types import SimpleNamespace as NS

from cartograph.agent import MAX_STEPS, Agent


def reply(*calls, text=None):
    tool_calls = [NS(id=f"c{i}", function=NS(name=n, arguments=json.dumps(a)))
                  for i, (n, a) in enumerate(calls)] or None
    msg = NS(tool_calls=tool_calls, content=text,
             model_dump=lambda **_: {"role": "assistant", "content": text})
    return NS(choices=[NS(message=msg)], usage=NS(total_tokens=100))


def make_agent(script):
    agent = Agent.__new__(Agent)  # skip __init__: no DB, no model download
    agent.mode, agent.model, agent.docs = "index", "fake", {1: None, 2: None, 3: None}
    replies = iter(script)
    agent.client = NS(chat=NS(completions=NS(create=lambda **_: next(replies))))
    agent.run_tool = lambda name, args: ("results", [3, 2])  # every tool "shows" F3, F2
    agent.last_extra, agent.api_error = {}, TimeoutError
    return agent


def test_api_error_ends_the_question_instead_of_the_run():
    def boom(**_):
        raise TimeoutError("runaway generation")

    agent = make_agent([])
    agent.client = NS(chat=NS(completions=NS(create=boom)))
    assert agent("q") == []
    assert agent.last_extra["events"][0]["type"] == "error"


def test_submitted_answer_ranks_first_then_seen_functions():
    agent = make_agent([
        reply(("search_meaning", {"query": "cookies"})),
        reply(("submit_answer", {"functions": ["F2", "F99", "bogus"]})),
    ])
    assert agent("where are cookies set?") == [2, 3]  # unknown ids dropped, F3 seen after
    extra = agent.last_extra
    assert extra["answer"] == [2] and extra["tokens"] == 200
    assert [e["type"] for e in extra["events"]] == ["tool", "answer"]


def test_answer_typed_as_text_counts_as_submission():
    agent = make_agent([reply(text='Done.\nsubmit_answer(["F3", "F1"])')])
    assert agent("q") == [3, 1] and agent.last_extra["events"][0]["from_text"]
    agent = make_agent([reply(text='{"name": "submit_answer", "arguments": {"functions": ["F2"]}}')])
    assert agent("q") == [2]
    agent = make_agent([reply(text="not_found")])
    assert agent("q") == [] and agent.last_extra["not_found"]


def test_text_reply_gets_nudged_and_budget_is_enforced():
    script = [reply(text="I think it is F1")] + [
        reply(("search_keyword", {"query": "x"})) for _ in range(MAX_STEPS)]
    agent = make_agent(script)
    assert agent("q") == [3, 2]  # never submitted: ranked by what it saw
    events = agent.last_extra["events"]
    assert events[0]["type"] == "text" and agent.last_extra["answer"] == []
    assert len(events) == MAX_STEPS + 1  # loop stops at the budget
