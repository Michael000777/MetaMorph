from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

load_dotenv("/home/jon/MetaMorph/.env")

llm = ChatOpenAI(model="gpt-4o")

'''
llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY")
)
'''

def get_llm() -> Runnable:
    return llm


#dynamic implementation, say user wants groq over chatgpt