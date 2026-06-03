#Validator agent implementation.

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from utils.llm import get_llm, ainvoke_with_backoff
from utils.prompts import get_prompt
from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.types import Command
from utils.MetaMorphState import ValidatorData, MetaMorphState, tracker
from .validation_contracts import validate_transformation_contract


MAX_RETRIES = 5


validator_prompt = get_prompt("validator_prompt")
#llm = get_llm()


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

    failed_rows_indices: List[int] = Field(..., 
                                                     description=(
            "A list of row indices that failed when comparing raw values to the transformed values and need to be corrected"
    ),
    json_schema_extra={"example": [0,67,127]},
    )
    


def determine_route(decision: str, retry_count: int = 0) -> str:

    if decision == "pass":
        return END
    elif decision == "retry" and retry_count < MAX_RETRIES:
        return "refinement_agent"  # name of the retry target
    else:
        return END


def validation_status(decision: str, retry_count: int = 0, *, model_error: bool = False) -> str:
    if decision == "pass":
        return "pass"
    if model_error:
        return "model_error" if retry_count >= MAX_RETRIES else "recoverable_retry"
    if decision == "retry" and retry_count < MAX_RETRIES:
        return "recoverable_retry"
    return "terminal_fail"

async def validator_node(state: MetaMorphState) -> Command:
    timestamp = datetime.now(timezone.utc).isoformat()

    raw = getattr(state, "input_column_data", None)
    refined = getattr(state, "refinement_results", None)
    parsed = getattr(state, "parsed_data_output", None)
    vd = getattr(state, "validator_data", None)
    retry_count = vd.retry_count if vd else 0
    #retry_count = getattr(state, "retry_count", 0) #there is no retry_count attr in state so i will update this.
   


    if refined and getattr(refined, "cleaned_values", None) is not None:
        transformed_values = refined.cleaned_values
        model_confidence = getattr(refined, "confidence", None)
    elif parsed and getattr(parsed, "parsed_output", None) is not None:
        transformed_values = parsed.parsed_output
        model_confidence = getattr(parsed, "model_confidence", None)
    else:
        transformed_values = []
        model_confidence = None

    curr_col = state.input_column_data.column_name if getattr(state, "input_column_data", None) else "unknown_column"
    output_names = None
    if parsed and getattr(parsed, "column_name", None):
        output_names = parsed.column_name.get(curr_col)

    contract_result = validate_transformation_contract(
        raw_values=(raw.values if raw else []),
        transformed_values=transformed_values,
        output_names=output_names,
        confidence=model_confidence,
    )

    if not contract_result.passed:
        decision = "retry" if contract_result.recoverable and retry_count < MAX_RETRIES else "fail"
        reason = f"Deterministic validation failed: {contract_result.message}"
        failed_rows = contract_result.failed_rows
        route = determine_route(decision, retry_count)
        status = validation_status(decision, retry_count)
        new_retry_count = retry_count + 1 if decision == "retry" else retry_count

        print(f"Validation: {decision.upper()} — {reason}", flush=True)

        NodeTrackerName = f"validator@{timestamp}"
        V_PATCH = {
            "processed_column": [curr_col],
            "node_path": {curr_col: {NodeTrackerName: reason}},
            "events_path": [f"ValidatorNode@{timestamp}"],
        }

        return Command(
            update={
                "validator_data": ValidatorData(
                    passed=False,
                    failed_rows=failed_rows,
                    message=reason,
                    retry_count=new_retry_count,
                    status=status,
                    final_route=route,
                ),
                "Node_Col_Tracker": V_PATCH,
            },
            goto=route,
        )

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
    decision, reason, conf, failed_rows = None, None, 0.0, []
    llm = get_llm("validator_agent")

    model_error = False

    try:
        #res = await llm.with_structured_output(
         #   ValidatorLLMOutput, method="function_calling"
        #).ainvoke(messages)

        r = llm.with_structured_output(ValidatorLLMOutput, method="function_calling")
        res = await ainvoke_with_backoff(r, messages)

        decision, reason, conf, failed_rows = res.decision, res.reason, res.confidence, res.failed_rows_indices
    except Exception as e:
        # Fallback behavior on LLM failure: treat as retry (bounded by MAX_RETRIES)
        model_error = True
        decision = "retry" if retry_count < MAX_RETRIES else "fail"
        reason = f"Validator LLM error: {e}"
        conf = 0.0

    print(f"Validation: {decision.upper()} — {reason}", flush=True)

    route = determine_route(decision, retry_count)
    status = validation_status(decision, retry_count, model_error=model_error)

    NodeTrackerName = f"validator@{timestamp}"
    
    #Tracker patch (merged by Node_Col_tracker
    V_PATCH = {
        "processed_column": [curr_col],
         "node_path": {curr_col: {NodeTrackerName: reason}},
         "events_path" : [f"ValidatorNode@{timestamp}"]
        # "events_path": [f"Validator → {('Refinement' if decision=='retry' else 'End' if decision=='pass' else 'Supervisor')}"]
     }

    new_retry_count = retry_count + 1 if decision == "retry" else retry_count


    return Command(
    update={
        "validator_data": ValidatorData(
            passed=(decision == "pass"),
            failed_rows=failed_rows, #I added in the row level checks.
            message=reason,
            retry_count=new_retry_count,
            status=status,
            final_route=route,
        ),
        #"messages": [HumanMessage(content=reason, name="validator")],
        #"validation_confidence": conf,
        #"retry_count": getattr(state, "retry_count", 0) + (1 if decision == "retry" else 0),
        "Node_Col_Tracker": V_PATCH,
    },
    goto=route,
)
