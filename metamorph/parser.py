import sys
from pathlib import Path
from pydantic.v1 import BaseModel, Field, constr, confloat
from typing import Annotated, Sequence, List, Literal, Optional
from langgraph.types import Command
from datetime import datetime, timezone

import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, parsedData


llm = get_llm()

parser_prompt = get_prompt("parser_prompt")

ConfidenceFloat = Annotated[float, Field(ge=0.0, le=1.0)]
LongStr = Annotated[str, Field(min_length=10)]

class StructureParserOutput(BaseModel):
    column: str = Field(
        ..., 
        description=(
            "The name of the input column that has been parsed. "
            "Example values include: 'age_col', 'Date', 'Location', 'Strain_ID', "
            "'Replicate', 'Inoculation_date'."
    ),
        example="Strain_ID"
    )

    parsed_col_data: List[Optional[str]] = Field(
        ..., 
        description=(
            "A list of parsed values corresponding to the input column. "
            "Each element represents a value extracted or cleaned for a specific row. "
            "Should preserve row order."
        ),
        example=["strain_A", "strain_B", "strain_C"]
    )

    confidence: ConfidenceFloat = ...
    notes: LongStr = ...


async def parser_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:

    timestamp = datetime.now(timezone.utc).isoformat()

    messages = [
        {"role": "system", "content": parser_prompt},
        {
            "role": "user",
            
            #Serialize the composite payload to a JSON string for the LLM
            "content": json.dumps(
                {
                    "column_schema_information": state.schema_inference.model_dump(),
                    "input_column_information": state.input_column_data.model_dump(),
                },
                ensure_ascii=False,
            ),
        }
    ]

    response = await llm.with_structured_output(StructureParserOutput, method="function_calling").ainvoke(messages)

    curr_col = state.input_column_data.column_name
    
    expected_len = len(state.input_column_data.values)

    # --- Enforce row alignment (pad/truncate) ---
    vals = list(response.parsed_col_data)
    if len(vals) < expected_len:
        vals.extend([None] * (expected_len - len(vals)))
    elif len(vals) > expected_len:
        vals = vals[:expected_len]
        

    P_PATCH = { 
        "Node_Col_Tracker" : { 
            "node_path" : {
                curr_col: {
                    "ParserNode": response.notes
                    }
                },
            "events_path" : [f"ParserNode@{timestamp}"]
        },
        "parsed_data_output" : {
            "column_name" : response.column,
            "parsed_output" : vals,
            "model_confidence" : response.confidence,
            "notes" : response.notes
        }  
    }
    


    return Command(update=P_PATCH, goto="refinement_agent")

