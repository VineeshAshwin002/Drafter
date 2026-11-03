"""LangGraph workflow for creating and updating emails."""

from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .email_creator import generate_email, revise_email


class EmailState(TypedDict):
    user_request: str
    email_draft: str
    filename: str
    status: str


def create_draft(state: EmailState) -> dict[str, str]:
    return {
        "email_draft": generate_email(state["user_request"]),
        "status": "draft_created",
    }


def ask_update(
    state: EmailState,
) -> Command[Literal["update_email", "save_email"]]:
    answer = interrupt("Do you want to update the email?")
    if answer.get("answer", "").strip().lower() in {"yes", "y"}:
        update_request = answer.get("request", "").strip()
        if not update_request:
            raise ValueError("An update request is required when the answer is yes.")
        return Command(
            goto="update_email",
            update={"user_request": update_request},
        )
    if answer.get("answer", "").strip().lower() in {"no", "n"}:
        return Command(goto="save_email")
    raise ValueError("Answer must be yes or no.")


def update_email(state: EmailState) -> dict[str, str]:
    return {
        "email_draft": revise_email(state["user_request"], state["email_draft"]),
        "status": "updated",
    }


def save_email(state: EmailState) -> dict[str, str]:
    with open(state["filename"], "w", encoding="utf-8") as email_file:
        email_file.write(state["email_draft"])
    return {"status": "saved"}


def build_email_graph():
    graph = StateGraph(EmailState)
    graph.add_node("create_draft", create_draft)
    graph.add_node("ask_update", ask_update)
    graph.add_node("update_email", update_email)
    graph.add_node("save_email", save_email)
    graph.add_edge(START, "create_draft")
    graph.add_edge("create_draft", "ask_update")
    graph.add_edge("update_email", "ask_update")
    graph.add_edge("save_email", END)
    return graph.compile(checkpointer=MemorySaver())


email_graph = build_email_graph()


def start_email_workflow(user_request: str, filename: str | None = None) -> tuple[str, dict]:
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    state: EmailState = {
        "user_request": user_request,
        "email_draft": "",
        "filename": filename or "generated_email.txt",
        "status": "started",
    }
    result = email_graph.invoke(state, config)
    return thread_id, result


def resume_email_workflow(thread_id: str, review: dict[str, str]) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    return email_graph.invoke(Command(resume=review), config)
