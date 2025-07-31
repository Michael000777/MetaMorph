# Refinement.py implementatiion


from pydantic import BaseModel, Field
from typing import List, Any
from utils.llm import get_llm
from utils.prompts import get_prompt
from langchain_core.messages import HumanMessage
from langgraph.graph import MessagesState
from langgraph.types import Command

llm = get_llm()
refinement_prompt = get_prompt("refinement_prompt")

class Refinement(BaseModel):
    refined_values: List[Any] = Field(..., description="Cleaned, final metadata values")
    notes: str = Field(..., description="Explanation of changes or logic applied")

async def refinement_agent(state: MessagesState) -> Command:
    parser_output = state["output_metadata"]
    schema_output = state["schema_output"]
    raw_input = state["input_metadata"]

    # Combine all context into one user message
    user_message = (
        f"Original metadata column: {raw_input}\n\n"
        f"Initial parsed values: {parser_output}\n\n"
        f"Schema inference:\n"
        f"- Inferred type: {schema_output.get('inferred_type')}\n"
        f"- Format: {schema_output.get('format')}\n"
        f"- Notes: {schema_output.get('notes', '')}"
    )

    messages = [
        {"role": "system", "content": refinement_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        result = await llm.with_structured_output(Refinement).ainvoke(messages)
    except Exception as e:
        print(f"Refinement agent failed: {e}")
        return Command(
            update={
                "messages": [HumanMessage(content="Refinement agent failed.")],
            },
            goto="supervisor"
        )

    print(f"Refined values: {result.refined_values}\n Notes: {result.notes}")

    return Command(
        update={
            "output_metadata": result.refined_values,
            "refinement_notes": result.notes,
            "messages": [HumanMessage(content="Refinement complete.", name="refiner")]
        },
        goto="validator_agent"
    )
