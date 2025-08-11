from typing import Annotated, Sequence, List, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from IPython.display import Image, display
from dotenv import load_dotenv
from langchain_experimental.tools import PythonREPLTool
from uuid import uuid5, NAMESPACE_DNS
import pprint
import asyncio
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parent.parent))

from supervisor import supervisor_node
from utils.thread import generate_thread_id
from utils.MetaMorphState import MetaMorphState
from input import build_sample_data



memory = MemorySaver()


graph = StateGraph(MetaMorphState)

graph.add_node("supervisor", supervisor_node)
graph.add_node("...", ...)
graph.add_node("...", ...)
graph.add_node("...", ...)
graph.add_node("...", ...)
graph.add_node("...", ...)

graph.add_edge(START, "supervisor")
app = graph.compile(checkpointer=memory)

username = input("") #Used for persistence in memory 
thread_id = generate_thread_id(username)

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

#main
current_state = MetaMorphState()