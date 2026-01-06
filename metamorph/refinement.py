# Refinement.py implementatiion

from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from utils.llm import get_llm, ainvoke_with_backoff
from utils.prompts import get_prompt
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from utils.MetaMorphState import MetaMorphState, RefinementResults, tracker

from utils.tools import normalize_to_colmatrix

#llm = get_llm()
refinement_prompt = get_prompt("refinement_prompt")

JSONScalar = Union[str, int, float, bool, None]

class Refinement(BaseModel):
    refined_values: List[List[JSONScalar]] = Field(..., description="Cleaned, final metadata values")
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(None, description="Explanation of changes or logic applied")

    @field_validator("refined_values", mode="before")
    @classmethod
    def coerce_1d_to_2d(cls, v):
        if isinstance(v, list) and (len(v) == 0 or not isinstance(v[0], list)):
            return [v]
        return v


async def refinement_agent(state: MetaMorphState) -> Command:
    timestamp = datetime.now(timezone.utc).isoformat()

    parsed = state.parsed_data_output.parsed_output
    schema = state.schema_inference
    raw = state.input_column_data.values

    # Combine all context into one user message
    # Do we ignore passing raw inputs into the refiner again? token management
    #Now that we have the possibility of multiple columns per col do we pass all at once? yes for now as we don't want to pass raw and SI redundantly 

    user_message = (
        f"Original metadata column: {(raw if raw else {})}\n\n"
        f"Initial parsed values: {(parsed if parsed else {})}\n\n"
        f"Schema inference: {(schema.model_dump() if schema else {})}"
        )

    messages = [
        {"role": "system", "content": refinement_prompt},
        {"role": "user", "content": user_message}
    ]
    llm = get_llm()

    try:
        r = llm.with_structured_output(Refinement, method="function_calling")
        result = await ainvoke_with_backoff(r, messages)
        #result = await llm.with_structured_output(Refinement, method="function_calling").ainvoke(messages)
    except Exception as e:
        print(f"Refinement agent failed: {e}", flush=True)
        return Command(
            update={
                "messages": [HumanMessage(content="Refinement agent failed.")],
            },
            goto="validator_agent"
        )
        
    # Enforce row alignment with the source column
    expected = len(raw)
    vals = list(result.refined_values)

    for i, col_vals in enumerate(vals):
        if len(col_vals) < expected:
            vals[i] = col_vals + [None] * (expected - len(col_vals))
        elif len(col_vals) > expected:
            vals[i] = col_vals[:expected]
        
    
    

    
    

    print(f"Refined values: {vals}\nNotes: {result.notes}", flush=True)

    NormVals = normalize_to_colmatrix(vals)
    print(f"Refined Normalized values: {NormVals}", flush=True)


    # Read previous attempt count safely from Pydantic state
    prev = getattr(state, "refinement_results", None)
    prev_attempts = getattr(prev, "refinement_attempts", 0) if prev else 0

    # Produce a proper RefinementResults object (matches MetaMorphState schema)
    new_refinement = RefinementResults(
        cleaned_values=NormVals,
        confidence=result.confidence, #replaced default 1 with model derived confidence.
        refinement_attempts=prev_attempts + 1,
    )

    # Tracker patch (merged by Annotated[tracker, merge_tracker] on Node_Col_tracker)
    curr_col = state.input_column_data.column_name if getattr(state, "input_column_data", None) else "unknown_column"

    NodeTrackerName = f"RefinementNode@{timestamp}"

    R_PATCH = {
        "processed_column": [curr_col],
        "node_path": {curr_col: {NodeTrackerName: result.notes}},
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
