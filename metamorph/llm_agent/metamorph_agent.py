# llm_agent/metamorph_agent.py

from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.schema import SystemMessage
from langchain.tools import tool

@tool
def clean_text(text: str) -> str:
    """Strips whitespace, removes extra characters, and standardizes text case."""
    return text.strip().lower().replace("-", " ")

@tool
def parse_height(text: str) -> str:
    """Parses height expressions like '5 ft 10 in' or '170cm' into centimeters."""
    text = text.lower().strip()
    if "cm" in text:
        try:
            return str(int(text.replace("cm", "").strip()))
        except:
            return "unknown"
    elif "ft" in text:
        import re
        ft, inch = 0, 0
        match = re.match(r"(\d+)\s*ft\s*(\d+)?", text)
        if match:
            ft = int(match.group(1))
            if match.group(2):
                inch = int(match.group(2))
        cm = round((ft * 12 + inch) * 2.54)
        return str(cm)
    return "unknown"

def initialize_metamorph_agent():
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    tools = [
    Tool.from_function(
        func=clean_text,
        name="clean_text",
        description="Strips whitespace, removes extra characters, and standardizes text case."
    ),
    Tool.from_function(
        func=parse_height,
        name="parse_height",
        description="Parses height expressions like '5 ft 10 in' or '170cm' into centimeters."
    )
]


    system_msg = SystemMessage(content=(
        "You are a metadata processing agent. "
    "Your job is to intelligently clean and transform messy, unstructured column values into structured outputs. "
    "You may encounter human expressions like 'six feet tall', 'almost 170cm', or 'about five eleven'. "
    "Use the available tools to normalize these values into precise units. "
    "If the input is ambiguous, choose the most reasonable interpretation. "
    "Respond with a dictionary like {'parsed_height_cm': '180'}."
    ))

    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        agent_kwargs={"system_message": system_msg}
    )
