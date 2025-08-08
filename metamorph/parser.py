import sys
from pathlib import Path
from pydantic import BaseModel, Field, constr, confloat
from typing import Annotated, Sequence, List, Literal
from langgraph.types import Command

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt
from utils.MetaMorphState import MetaMorphState, parsedData

llm = get_llm()

parser_prompt = get_prompt("parser_prompt")

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

    parsed_col_data: List[str] = Field(
        ..., 
        description=(
            "A list of parsed values corresponding to the input column. "
            "Each element represents a value extracted or cleaned for a specific row. "
            "Should preserve row order."
        ),
        example=["strain_A", "strain_B", "strain_C"]
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., 
        description="A float between 0 and 1 representing the confidence level of the parser in the correctness of this transformation.",
        example=0.92
    )

    notes: constr(min_length=10) = Field(
        ..., 
        description=(
            "Detailed justification or rationale for the parsing results. "
            "Explain how the machine-readable output was derived from the original column, "
            "including any assumptions, heuristics, or rules applied."
        ),
        example=(
            "Parsed the 'Strain_ID' column by splitting on underscores and extracting strain identifiers. "
            "Filtered out replicates and control labels."
        )
    )



async def parser_node(state: MetaMorphState) -> Command[Literal["supervisor"]]:
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

    return Command(
        update={
            "parsed_data_output" : parsedData(
                column_name=response.column,
                parsed_output=response.parsed_col_data,
                model_confidence=response.confidence,
                notes=response.notes
            ),
        },
        goto="supervisor"
    )