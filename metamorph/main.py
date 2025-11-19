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
from uuid import uuid5, NAMESPACE_DNS
import pprint
import asyncio
import sys
from pathlib import Path


from schema_inference import schema_inference_node
from parser import parser_node
from refinement import refinement_agent
from validator import validator_node




sys.path.append(str(Path(__file__).resolve().parent.parent))

from supervisor import supervisor_node
from utils.thread import generate_thread_id
from utils.MetaMorphState import MetaMorphState, InputColumnData
from input import build_sample_data



memory = MemorySaver()


graph = StateGraph(MetaMorphState)

graph.add_node("supervisor", supervisor_node)
graph.add_node("schema_inference", schema_inference_node)
graph.add_node("parser_agent", parser_node)
graph.add_node("refinement_agent", refinement_agent)
graph.add_node("validator_agent", validator_node)
#graph.add_node("...", ...)

graph.add_edge(START, "supervisor")
app = graph.compile(checkpointer=memory)

username = input("").strip()  #Used for persistence in memory 
thread_id = generate_thread_id(username)

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

#main
#current_state = MetaMorphState()

# Example column

import pandas as pd
s = pd.Series(["5 ft 10 in", "170 cm", "6'2\"", None, "180cm", "1.75 m"], name="height")

# Build samples for schema inference context
col_sample = build_sample_data(s)

# Seed initial state
initial_state = MetaMorphState(
    input_column_data=InputColumnData(column_name=s.name or "unknown", values=s.tolist()),
    ColumnSample=col_sample,
)

# Invoke the graph (Supervisor will decide next steps)
final_state = asyncio.run(app.ainvoke(initial_state, config))
print(final_state)