import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Sequence, List, Literal
from langgraph.types import Command
from datetime import datetime, timezone
import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm, ainvoke_with_backoff
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, SchemaInferenceResults

#llm = get_llm()

schema_system_prompt = get_prompt("schema_inference_prompt")

class SchemaInference(BaseModel):
    Inferred_type: str = Field(description="The semantic type of the input column, e.g., 'age', 'date', 'location'.")
    conf: float = Field(description="A number between 0 and 1 representing the your confidence in the inferred type.")
    reason: str = Field(
        description="Detailed justification for ..., explaining the rationale behind ..."
    )



async def schema_inference_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:
    

    timestamp = datetime.now(timezone.utc).isoformat()

    payload = json.dumps(
        state.ColumnSample.model_dump(mode="json", exclude=None),
        ensure_ascii=False, separators=(",", ":"), default=str
        )

    messages = [
        {"role": "system", "content": schema_system_prompt},
        {
            "role": "user",
            "content": payload
        } 
    ]
    llm = get_llm()

    r = llm.with_structured_output(SchemaInference)
    response = await ainvoke_with_backoff(r, messages)

    #response = await llm.with_structured_output(SchemaInference).ainvoke(messages)

    curr_col = state.input_column_data.column_name

    print(f"--- MetaMorph Transitioning: Schema Inference → Supervisor ---", flush=True)

    print(f"Inferred Schema: {response.Inferred_type}", flush=True)
    print(f"Confidence: {response.conf}", flush=True)
    print(f"Notes: {response.reason}", flush=True)

    NodeTrackerName = f"SchemaInferenceNode@{timestamp}"

    SI_PATCH = {
        "schema_inference" : {
            "inferred_type" : response.Inferred_type,
            "confidence" : response.conf,
            "notes" : response.reason
        },
        "Node_Col_Tracker" : { 
            "node_path" : {
                curr_col: {
                    NodeTrackerName: response.reason
                    }
                },
            "events_path" : [f"SchemaInferenceNode@{timestamp}"]
        }
    }

    return Command(
        update=SI_PATCH,
        goto="supervisor"
    )

