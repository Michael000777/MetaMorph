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

llm = get_llm()

Supervisor_system_prompt = get_prompt("Supervisor_system_prompt")


#TO DO: edit system prompt message to reflect the agents available to the supervisor node. 


class Supervisor(BaseModel):
    next: Literal["agent1", "agent2", "agent3"] = Field(
        description="Determines which agent specialist to activate next in the workflow sequence: "
        "'Agent1' when ..."
        "'Agent2' when ..."
        "'Agent3' when ..."
    )
    justification: str = Field(
        description="Detailed justification for the routing decision, explaining the rationale behind selecting the particular specialist and how this advances the task toward completion"
    )


async def supervisor_node(state: MessagesState) -> Command[Literal["SchemaInference", "Parser", "Refiner", "Validator"]]: #update with names used to compile graph!

    timestamp = datetime.now(timezone.utc).isoformat()

    messages = [
        {"role": "system", "content": Supervisor_system_prompt},
    ]

    response = await llm.with_structured_output(Supervisor).ainvoke(messages)

    goto = response.next
    reason = response.justification

    print(f"--- MetaMorph Transitioning: Supervisor → {goto.upper()} ---") #Key for initial validation, and see transitional steps.

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
