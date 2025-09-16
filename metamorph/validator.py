#Validator agent implementation.


from pydantic import BaseModel, Field
from typing import Literal
from utils.llm import get_llm
from utils.prompts import get_prompt
from langchain_core.messages import HumanMessage
from langgraph.graph import START, END, MessagesState
from langgraph.types import Command
from utils.MetaMorphState import ValidatorData, MetaMorphState, tracker


MAX_RETRIES = 5

validator_prompt = get_prompt("validator_prompt")
llm = get_llm()


class ValidatorLLMOutput(BaseModel):
    decision: Literal["pass", "retry", "fail"] = Field(...,
        description= "Decision"
    )
    
    reason: str = Field(...,
        description = "Why this decision was made"
    )
    
    confidence: float = Field(...,
        ge=0.0, le=1.0,
        description="Confidence score for this decision (0–1)"

    )
    


def determine_route(decision: str, retry_count: int = 0) -> str:
    if decision == "pass":
        return END #Using this for now; need to update with either end_pass or end_fail for more visibility.
    elif decision == "retry" and retry_count < MAX_RETRIES:
        return "refinement_agent"  # name of the retry target
    else:
        return "supervisor"

async def validator_node(state: MetaMorphState) -> Command:
    raw = getattr(state, "input_column_data", None)
    refined = getattr(state, "refinement_results", None)
    parsed = getattr(state, "parsed_data_output", None)
    retry_count = getattr(state, "retry_count", 0)


    input_vals = (raw.values if raw else []) or []
    
    
    if refined and getattr(refined, "cleaned_values", None) is not None:
        transformed_values = refined.cleaned_values
    elif parsed and getattr(parsed, "parsed_output", None) is not None:
        transformed_values = parsed.parsed_output
    else:
        transformed_values = []

    messages = [
        {"role": "system", "content": validator_prompt},
        {"role": "user", 
         "content": (
             f"Input: {(raw.model_dump() if raw else {})}\n"
             f"Output: {transformed_values}"
         ),
        },
    ]
    
    # Initialize defaults so later code never references undefined names
    decision, reason, conf = None, None, 0.0

    try:
        res = await llm.with_structured_output(
            ValidatorLLMOutput, method="function_calling"
        ).ainvoke(messages)
        decision, reason, conf = res.decision, res.reason, res.confidence
    except Exception as e:
        # Fallback behavior on LLM failure: treat as retry (bounded by MAX_RETRIES)
        decision = "retry" if retry_count < MAX_RETRIES else "fail"
        reason = f"Validator LLM error: {e}"
        conf = 0.0

    print(f"Validation: {decision.upper()} — {reason}", flush=True)

    route = determine_route(decision, getattr(state, "retry_count", 0))
    
    #Tracker patch (merged by Node_Col_tracker
    curr_col = state.input_column_data.column_name if getattr(state, "input_column_data", None) else "unknown_column"
    V_PATCH = {
        "processed_column": [curr_col],
         "node_path": {curr_col: {"validator": decision}},
         "events_path": [f"Validator → {('Refinement' if decision=='retry' else 'End' if decision=='pass' else 'Supervisor')}"]
     }



    return Command(
    update={
        "validator_data": ValidatorData(
            passed=(decision == "pass"),
            failed_rows=[], #populate if you have add row level checks
            message=reason,
        ),
        "messages": [HumanMessage(content=reason, name="validator")],
        "validation_confidence": conf,
        "retry_count": getattr(state, "retry_count", 0) + (1 if decision == "retry" else 0),
        "Node_Col_tracker": V_PATCH,
    },
    goto=route,
)
