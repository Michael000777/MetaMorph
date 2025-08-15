#Implementation of supervisor agent.

#Using pydantic structures to make LLM outputs semi determinitsic 
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Sequence, List, Literal
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt

from utils.MetaMorphState import MetaMorphState

llm = get_llm()

Supervisor_system_prompt = get_prompt("Supervisor_system_prompt")


#TO DO: edit system prompt message to reflect the agents available to the supervisor node. 


class Supervisor(BaseModel):
    next: Literal["schema_inference", "parser_agent", "refinement_agent", "validator_agent"] = Field(
        description="Determines which agent specialist to activate next in the workflow sequence: "
        "'schema_inference' when the data type or structure of the column needs to be inferred."
        "'parser_agent' when raw data needs to be parsed and transformed."
        "'refinement_agent' when parsed data needs cleaning or normalization."
        "'validator_agent' when output needs final verification."
    )
    justification: str = Field(
        description="Detailed justification for the routing decision, explaining the rationale behind selecting the particular specialist and how this advances the task toward completion"
    )


async def supervisor_node(state: MetaMorphState) -> Command[Literal["schema_inference", "parser_agent", "refinement_agent", "validator_agent"]]: #update with names used to compile graph!

    timestamp = datetime.now(timezone.utc).isoformat()
    
    curr_col = state.input_column_data.column_name or "unknown"
    already_inferred = bool(getattr(state, "schema_inference", None)
                            and state.schema_inference.inferred_type)
    
    
    # Safety: if events show SchemaInferenceNode ran at least once, also treat as inferred
    events = getattr(getattr(state, "Node_Col_Tracker", None), "events_path", []) or []
    seen_schema = any(e.startswith("SchemaInferenceNode@") for e in events)
    already_inferred = already_inferred or seen_schema


    if not already_inferred:
        goto = "schema_inference"
        reason = f"No schema yet for '{curr_col}'. Routing to schema_inference."
    else:
        goto = "parser_agent"
        reason = f"Schema already inferred for '{curr_col}'. Advancing to parser_agent."

    '''
    messages = [
        {"role": "system", "content": Supervisor_system_prompt},
    ]

    response = await llm.with_structured_output(Supervisor).ainvoke(messages)

    goto = response.next
    reason = response.justification
    '''
    print(f"--- MetaMorph Transitioning: Supervisor → {goto.upper()} ---") #Key for initial validation, and see transitional steps.

    

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
