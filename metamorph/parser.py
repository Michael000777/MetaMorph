import sys
from pathlib import Path
from pydantic import BaseModel, Field, constr, confloat
from typing import Annotated, Sequence, List, Literal
from langgraph.types import Command
from datetime import datetime, timezone

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, parsedData


llm = get_llm()

parser_prompt = get_prompt("parser_prompt")

ConfidenceFloat = Annotated[float, Field(ge=0.0, le=1.0)]
LongStr = Annotated[str, Field(min_length=10, strip_whitespace=True)]

class StructureParserOutput(BaseModel):
    column: str = Field(
        ..., 
        description=(
            "The name of the input column that has been parsed. "
            "Example values include: 'age_col', 'Date', 'Location', 'Strain_ID', "
            "'Replicate', 'Inoculation_date'."
    ),
    json_schema_extra={"example": ["Strain_ID"]},
    )

    parsed_col_data: List[str] = Field(
        ..., 
        description=(
            "A list of parsed values corresponding to the input column. "
            "Each element represents a value extracted or cleaned for a specific row. "
            "Should preserve row order."
        ),
        json_schema_extra={"examples": [["strain_A", "strain_B", "strain_C"]]},
    )

    confidence: ConfidenceFloat = Field(
        ...,
        description="A float between 0 and 1 representing the confidence level."
    )

    notes: LongStr = Field(
        ..., 
        description=(
            "Detailed justification or rationale for the parsing results. "
            "Explain how the machine-readable output was derived from the original column, "
            "including any assumptions, heuristics, or rules applied."
        ),
        json_schema_extra={"examples": [
            "Parsed the 'Strain_ID' column by splitting on underscores and extracting strain identifiers. "
            "Filtered out replicates and control labels."
        ]},   
        )
    



async def parser_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:

    timestamp = datetime.now(timezone.utc).isoformat()

    messages = [
        {"role": "system", "content": parser_prompt},
        {
            "role": "user",
            "content": {
                "column schema information": state.schema_inference.model_dump(),
                "Input column information": state.input_column_data.model_dump()
            }
        }
    ]

    response = await llm.with_structured_output(StructureParserOutput).ainvoke(messages)

    curr_col = state.input_column_data.column_name

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
            "parsed_output" : response.parsed_col_data,
            "model_confidence" : response.confidence,
            "notes" : response.notes
        }  
    }
    


    return Command(update=P_PATCH, goto="supervisor")

