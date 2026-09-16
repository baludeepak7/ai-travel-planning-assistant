import asyncio
import sys

import streamlit as st

from src.config import Settings, configure_logging
from src.llm_factory import chat_model
from src.mcp_client.client import MCPClient
from src.models import TravelPreferences
from src.orchestration.assistant import TravelAssistant
from src.orchestration.context_manager import ContextManager
from src.rag.retriever import Retriever

configure_logging()
st.set_page_config(page_title="Singapore Travel Assistant", page_icon="🌏", layout="wide")
st.title("Singapore Travel Assistant")
st.caption("Grounded destination knowledge · MCP weather and currency · Your trip preferences")
settings = Settings()


def run_async(coroutine):
    # Keep the same loop across reruns: reusable async model clients are loop-bound.
    if "async_runner" not in st.session_state:
        factory = asyncio.ProactorEventLoop if sys.platform == "win32" else None
        st.session_state.async_runner = asyncio.Runner(loop_factory=factory)
    return st.session_state.async_runner.run(coroutine)


if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.preferences = TravelPreferences()

with st.sidebar:
    st.header("Destination: Singapore")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.preferences = TravelPreferences()
        st.rerun()
    st.toggle("Debug provenance", value=settings.debug_provenance, key="debug")

try:
    settings.validate_llm()
    if "assistant" not in st.session_state:
        with st.spinner("Loading knowledge base and discovering MCP tools…"):
            retriever = Retriever(settings)
            client = MCPClient()
            run_async(client.initialize())
            model = chat_model(settings)
            st.session_state.assistant = TravelAssistant(model, retriever, client)
            st.session_state.context = ContextManager(model)
    assistant = st.session_state.assistant
except Exception as exc:
    with st.sidebar:
        st.write("Knowledge base: setup required")
        st.write("Weather: Unavailable")
        st.write("Currency: Unavailable")
    st.error(
        str(exc)
        if isinstance(exc, (ValueError, RuntimeError))
        else "Startup failed. Check .env, dependencies and run python scripts/verify_setup.py."
    )
    st.stop()

with st.sidebar:
    st.success(f"Knowledge base: Ready · {assistant.retriever.count} indexed chunks")
    st.write("Weather: " + assistant.mcp.status["weather"])
    st.write("Currency: " + assistant.mcp.status["currency"])
    st.caption("Connected means MCP discovery succeeded; provider status is shown per request.")
    st.subheader("Retained preferences")
    st.json(st.session_state.preferences.model_dump(mode="json", exclude_none=True))


def show_message(entry):
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry.get("provenance"):
            with st.expander("Sources & execution details", expanded=st.session_state.debug):
                st.json(entry["provenance"])


for entry in st.session_state.messages:
    show_message(entry)

if message := st.chat_input("Ask about your Singapore trip"):
    history = [{"role": e["role"], "content": e["content"]} for e in st.session_state.messages[-8:]]
    st.session_state.messages.append({"role": "user", "content": message})
    show_message(st.session_state.messages[-1])
    with st.spinner("Checking your preferences, sources and requested tools…"):
        try:
            preferences, warning = run_async(
                st.session_state.context.update(st.session_state.preferences, message)
            )
            st.session_state.preferences = preferences
            response = run_async(assistant.respond(message, preferences, history))
            content = response.markdown + ("\n\n" + warning if warning else "")
            entry = {
                "role": "assistant",
                "content": content,
                "provenance": response.provenance.model_dump(mode="json"),
            }
        except Exception:
            entry = {
                "role": "assistant",
                "content": "The request could not be completed. "
                "Check the LLM connection and knowledge base, then try again. "
                "Your saved preferences are retained; no current data has been estimated.",
            }
        st.session_state.messages.append(entry)
    st.rerun()
