#Implementation of supervisor agent.

#Using pydantic structures to make LLM outputs semi determinitsic 
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Sequence, List, Literal
#from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
#from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm, ainvoke_with_backoff
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState

llm = get_llm()

Supervisor_system_prompt = get_prompt("Supervisor_system_prompt")


class Supervisor(BaseModel):
    next: Literal["schemaInference", "parser_agent", "refinement_agent", "validator_agent"] = Field(
        description="Determines which agent specialist to activate next in the workflow sequence: "
        "'schemaInference' when the data type or structure of the column needs to be inferred."
        "'parser_agent' when raw data needs to be parsed and transformed."
        "'refinement_agent' when parsed data needs cleaning or normalization."
        "'validator_agent' when output needs final verification."
    )
    justification: str = Field(
        description="Detailed justification for the routing decision, explaining the rationale behind selecting the particular specialist and how this advances the task toward completion"
    )


async def supervisor_node(state: MetaMorphState) -> Command[Literal["schemaInference", "parser_agent", "refinement_agent", "validator_agent"]]: #update with names used to compile graph!

    timestamp = datetime.now(timezone.utc).isoformat()

    #context rotuing 
    events = getattr(getattr(state, "Node_Col_Tracker", None), "events_path", []) or [] # we may not need this fallback as our default factories were specified 

    if events:
        event_context = "Node visited for this column: " + "->".join(map(str, events)) #is this is enough? might need performance eval and experimentation.
    else:
        event_context = "Current column has not been processed yet"


    messages = [
        {"role": "system", "content": Supervisor_system_prompt},
        {"role": "user", "content" : event_context}
    ]

    r = llm.with_structured_output(Supervisor)
    response = await ainvoke_with_backoff(r, messages)
    #response = await llm.with_structured_output(Supervisor).ainvoke(messages)

    goto = response.next
    reason = response.justification

    print(f"--- MetaMorph Transitioning: Supervisor → {goto.upper()} ---", flush=True) #Key for initial validation, and see transitional steps.

    print(f"Supervisor Justificaiton: {reason}", flush=True)

    curr_col = state.input_column_data.column_name

    SUP_PATCH = { 
        "Node_Col_Tracker" : { 
            "node_path" : {
                curr_col: {
                    "SupervisorNode": reason
                    }
                },
            "events_path" : [f"SupervisorNode@{timestamp}"]
        }
    }

    return Command(
        update=SUP_PATCH,
        goto=goto,
    )
