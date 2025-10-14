# Refinement.py implementatiion

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from utils.llm import get_llm
from utils.prompts import get_prompt
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from utils.MetaMorphState import MetaMorphState, RefinementResults, tracker

llm = get_llm()
refinement_prompt = get_prompt("refinement_prompt")

JSONScalar = Union[str, int, float, bool, None]

class Refinement(BaseModel):
    refined_values: List[List[JSONScalar]] = Field(..., description="Cleaned, final metadata values")
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(None, description="Explanation of changes or logic applied")

async def refinement_agent(state: MetaMorphState) -> Command:
    timestamp = datetime.now(timezone.utc).isoformat()

    parsed = state.parsed_data_output
    schema = state.schema_inference
    raw = state.input_column_data

    # Combine all context into one user message
    # Do we ignore passing raw inputs into the refiner again? token management
    #Now that we have the possibility of multiple columns per col do we pass all at once? yes for now as we don't want to pass raw and SI redundantly 

    user_message = (
        f"Original metadata column: {(raw.model_dump() if raw else {})}\n\n"
        f"Initial parsed values: {(parsed.model_dump() if parsed else {})}\n\n"
        f"Schema inference: {(schema.model_dump() if schema else {})}"
        )

    messages = [
        {"role": "system", "content": refinement_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        result = await llm.with_structured_output(Refinement, method="function_calling").ainvoke(messages)
    except Exception as e:
        print(f"Refinement agent failed: {e}", flush=True)
        return Command(
            update={
                "messages": [HumanMessage(content="Refinement agent failed.")],
            },
            goto="validator_agent"
        )
        
    # Enforce row alignment with the source column
    expected = len(raw.values)
    vals = list(result.refined_values)

    for new_col in vals: #updated to accomodate multiple columns.
        if len(new_col) < expected:
            new_col += [None] * (expected - len(new_col))
        elif len(new_col) > expected:
            new_col = new_col[:expected]
        
    
    

    
    

    print(f"Refined values: {vals}\nNotes: {result.notes}", flush=True)

    # Read previous attempt count safely from Pydantic state
    prev = getattr(state, "refinement_results", None)
    prev_attempts = getattr(prev, "refinement_attempts", 0) if prev else 0

    # Produce a proper RefinementResults object (matches MetaMorphState schema)
    new_refinement = RefinementResults(
        cleaned_values=vals,
        confidence=result.confidence, #replaced default 1 with model derived confidence.
        refinement_attempts=prev_attempts + 1,
    )

    # Tracker patch (merged by Annotated[tracker, merge_tracker] on Node_Col_tracker)
    curr_col = state.input_column_data.column_name if getattr(state, "input_column_data", None) else "unknown_column"
    R_PATCH = {
        "processed_column": [curr_col],
        "node_path": {curr_col: {"refinement": result.notes}},
        "events_path" : [f"RefinementNode@{timestamp}"]
        #"events_path": ["Refinement → Validator"]
    }

    return Command(
        update={
            "refinement_results": new_refinement,
            "Node_Col_Tracker": R_PATCH,
            "messages": [HumanMessage(content=f"Refinement complete: {result.notes}", name="refiner")], #where from messages? Upated node path to take the notes.
        },
        goto="validator_agent",
    )
