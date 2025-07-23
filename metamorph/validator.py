#metamorph_validator.py




from pydantic import BaseModel, Field
from typing import Literal
import asyncio


#from prompts import metamorph_validator_prompt

from utils.llm import get_llm
from utils.prompts import get_prompt

import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.types import Command

validator_prompt = get_prompt("validator_prompt")

llm = get_llm()

class Validator(BaseModel):
    decision: Literal["pass", "retry", "fail"] = Field(
        description= "Decision on the validity of the transformation"
    )
    
    reason: str = Field(
        description = "Explanation for the decision"
    )
    
    confidence: str = Field(
        ge=0.0, le=1.0,
        description="Confidence score for this decision (0–1)"

    )
    
#MAX_RETRIES = 5

#def determine_route(decision: str, retry_count: int = 0) -> str:
def determine_route(decision: str) -> str:
    if decision == "pass":
        return "__end__"
    #elif decision == "retry" and retry_count < MAX_RETRIES:
    elif decision == "retry":
        return "parser_agent"  # name of the retry target
    else:
        return "supervisor"

async def validator_node(state: MessagesState) -> Command:
    raw_input = state["input_metadata"]
    transformed = state["output_metadata"]

    messages = [
        {"role": "system", "content": validator_prompt},
        {"role": "user", "content": f"Input: {raw_input}\nOutput: {transformed}"}
    ]

    result = await llm.with_structured_output(Validator).ainvoke(messages)

    # Decide routing
    
    route = determine_route(result.decision)
    '''
    if result.decision == "pass":
        goto = "__end__"
    elif result.decision == "retry":
        goto = ""
    else:
        goto = "supervisor"
        
    '''

    print(f"🔍 Validation: {result.decision.upper()} — {result.reason}")

    return Command(
        update={"messages": [HumanMessage(content=result.reason, name="validator")],
                 "validation_confidence": result.confidence
                 #"retry_count": retry_count + 1 if result.decision == "retry" else retry_count},'''
        },
        goto=route
    )
