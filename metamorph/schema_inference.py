import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated, Sequence, List, Literal
from langgraph.types import Command

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, SchemaInferenceResults

llm = get_llm()

schema_system_prompt = get_prompt("schema_inference_prompt")

class SchemaInference(BaseModel):
    Inferred_type: str = Field(description="The semantic type of the input column, e.g., 'age', 'date', 'location'.")
    conf: float = Field(description="A number between 0 and 1 representing the your confidence in the inferred type.")
    reason: str = Field(
        description="Detailed justification for ..., explaining the rationale behind ..."
    )



async def schema_inference_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:

    messages = [
        {"role": "system", "content": schema_system_prompt},
        {
            "role": "user",
            "content": state.ColumnSample.model_dump()
        } 
    ]

    response = await llm.with_structured_output(SchemaInference).ainvoke(messages)


    print(f"--- MetaMorph Transitioning: Schema Inference → Supervisor ---")

    return Command(
        update={
            "schema_inference": SchemaInferenceResults(
                inferred_type=response.Inferred_type,
                confidence=response.conf,
                notes=response.reason
            ),
        },
        goto="supervisor"
    )