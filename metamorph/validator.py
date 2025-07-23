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
        description= ""
    )
    
    reason: str = Field(
        description = ""
    )


async def validator_node(state: MessagesState) -> Command:
    raw_input = state["input_metadata"]
    transformed = state["output_metadata"]

    messages = [
        {"role": "system", "content": validator_prompt},
        {"role": "user", "content": f"Input: {raw_input}\nOutput: {transformed}"}
    ]

    result = await llm.with_structured_output(Validator).ainvoke(messages)

    # Decide routing
    if result.decision == "pass":
        goto = "__end__"
    elif result.decision == "retry":
        goto = ""
    else:
        goto = "supervisor"

    print(f"🔍 Validation: {result.decision.upper()} — {result.reason}")

    return Command(
        update={"messages": [HumanMessage(content=result.reason, name="validator")]},
        goto=goto
    )
