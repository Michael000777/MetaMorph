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
graph.add_node("schemaInference", schema_inference_node)
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

test_data = [
  "177.8 cm",
  "5'10\"",
  "5 ft 10 in",
  "70in",
  "1.78 m",
  "approx 180 cm",
  " ~180cm ",
  "N/A",
  "",
  "—",
  "6'2\"",
  "6 ft 0 in",
  "172cm",
  "170 cm",
  "1.80 m",
  "1,800 mm",
  "5’9”",
  "5ft9in",
  "5-9",
  "about 5'7\"",
  "67\"",
  "200 cm",
  "2.00 m",
  "4'11\"",
  "?",
  "nil",
  "unknown",
  "NaN",
  "5 ft",
  "72 inches",
  "1.65m",
  "~ 165 cm",
  "Height: 180cm",
  "Height=175 cm",
  "approx. 5′11″",
  "5’ 11”",
  "5 11",
  "180",
  "1.755 m",
  "5ft 8\"",
  "5 ft, 8 in",
  "5′8″",
  "5’8",
  "68 in",
  "1.70 m",
  "   169 cm   ",
  "171 cm",
  "5ft 10\"",
  "6 feet",
  "180.0cm"
]


test_col = pd.Series(test_data, name="height")

col_sample = build_sample_data(test_col)

init = MetaMorphState(
    input_column_data=InputColumnData(
        column_name=test_col.name, #can't allow uknown col name yet. might be overwritten if there are multiple.
        values=test_col.tolist()),
    ColumnSample=col_sample,
    )

final_state = asyncio.run(app.ainvoke(init, config=config))

print(f"Final output: {final_state}")

