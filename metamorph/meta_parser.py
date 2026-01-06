import sys
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Sequence, List, Literal, Dict, Optional, Union
from langgraph.types import Command
from datetime import datetime, timezone
import json

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm, ainvoke_with_backoff
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, parsedData
from utils.tools import normalize_to_colmatrix


#llm = get_llm()

parser_prompt = get_prompt("parser_prompt")

#ConfidenceFloat = Annotated[float, Field(ge=0.0, le=1.0)]
#LongStr = Annotated[str, Field(min_length=10, strip_whitespace=True)]

JSONScalar = Union[str, int, float, bool, None]


class ColumnMap(BaseModel):
    input: str = Field(..., description="Input column name.")
    outputs: List[str] = Field(..., description="Extracted column names.")


class StructureParserOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    column: List[ColumnMap] = Field(
        ...,
        description="Mappings from the input column to extracted columns."
    )
    parsed_col_data: List[List[JSONScalar]] = Field(
        ...,
        description=(
            "Columns-first matrix. Outer list length = K (extracted columns). "
            "Each inner list length = N (rows), row order preserved."),
    )
    confidence: float = Field(..., ge=0.0, le=1.0,
        description="Confidence in [0,1].")
    notes: str = Field(..., min_length=1,
        description="Rationale for parsing decisions.")



async def parser_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:

    timestamp = datetime.now(timezone.utc).isoformat()

    if not state.input_column_data.values:
        raise ValueError("No column data loaded")
    
    num_rows = len(state.input_column_data)

    #Null value guard rail
    non_null_vals = state.input_column_data.n_non_null

    if num_rows and non_null_vals / num_rows < 0.5:
        raise ValueError("Too many nulls for reliable agent parsing!!")
    
    payload = {
                "column schema information": state.schema_inference.model_dump(mode="json", exclude=None),
                "Input column information": state.input_column_data.model_dump(mode="json", exclude=None)
            }
    
    payload_content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)

    messages = [
        {"role": "system", "content": parser_prompt},
        {
            "role": "user",
            "content": payload_content
        },
    ]

    #response = await llm.with_structured_output(
    #    StructureParserOutput
     #   ).ainvoke(messages)
    llm = get_llm()
    
    r = llm.with_structured_output(StructureParserOutput)
    response = await ainvoke_with_backoff(r, messages)
    
    col_dict = {m.input: m.outputs for m in response.column}

    print(f"--- MetaMorph Transitioning: Parser → Supervisor ---", flush=True)

    print(f"Parser Output: {response.parsed_col_data}", flush=True)
    print(f"Parser Confidence: {response.confidence}", flush=True)
    print(f"Notes: {response.notes}", flush=True)

    curr_col = state.input_column_data.column_name

    normParsed = normalize_to_colmatrix(response.parsed_col_data)

    NodeTrackerName = f"ParserNode@{timestamp}"

    P_PATCH = { 
        "Node_Col_Tracker" : { 
            "node_path" : {
                curr_col: {
                    NodeTrackerName: response.notes
                    }
                },
            "events_path" : [f"ParserNode@{timestamp}"]
        },
        "parsed_data_output" : {
            "column_name" : col_dict,
            "parsed_output" : normParsed, #response.parsed_col_data,
            "model_confidence" : response.confidence,
            "notes" : response.notes
        },  
    }
    


    return Command(update=P_PATCH, goto="supervisor")

