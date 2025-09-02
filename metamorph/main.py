#from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from IPython.display import Image, display
from dotenv import load_dotenv
from langchain_experimental.tools import PythonREPLTool
from uuid import uuid5, NAMESPACE_DNS
import pprint
import asyncio
import sys
from pathlib import Path
import pandas as pd



from supervisor import supervisor_node
from schema_inference import schema_inference_node
from meta_parser import parser_node
from refinement import refinement_agent
from validator import validator_node


sys.path.append(str(Path(__file__).resolve().parent.parent))



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


graph.set_entry_point("supervisor")


app = graph.compile(checkpointer=memory)

username = input("Username for session: ").strip() #Used for persistence in memory 
thread_id = generate_thread_id(username)

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

#Testing
data =  ["5 ft 10 in", "170 cm", "6'2\"", None, "180cm", "1.75 m"]
test_col = pd.Series(data, name="height")

col_sample = build_sample_data(test_col)

init = MetaMorphState(
    input_column_data=InputColumnData(
        column_name=test_col.name, #can't allow uknown col name yet. might be overwritten if there are multiple.
        values=test_col.tolist()),
    ColumnSample=col_sample,
    )

final_state = asyncio.run(app.ainvoke(init, config=config))

print(f"Final output: {final_state}")

