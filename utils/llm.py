from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
#from langchain_groq import ChatGroq

load_dotenv()

llm = ChatOpenAI(model="gpt-4o")

def get_llm() -> Runnable:
    return llm


#dynamic implementation, say user wants groq over chatgpt