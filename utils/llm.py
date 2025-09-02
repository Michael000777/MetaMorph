from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
#from langchain_groq import ChatGroq

load_dotenv("/Users/michael/Documents/Bioinformatics/Personal_Projects/ML/MetaMorph/.env")

llm = ChatOpenAI(model="gpt-4o")

def get_llm() -> Runnable:
    return llm


#dynamic implementation, say user wants groq over chatgpt