from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
#from langchain_groq import ChatGroq

import asyncio
import random
from openai import RateLimitError, APIError, APITimeoutError
import os

load_dotenv()

_LLM_MODEL = None
_LLM_INSTANCE = None

def set_llm_model(model_name: str):
    global _LLM_MODEL, _LLM_INSTANCE
    _LLM_MODEL = model_name
    _LLM_INSTANCE = None  # reset if model changes

def get_llm():
    global _LLM_INSTANCE
    if not _LLM_MODEL:
        raise ValueError("LLM model not set. Call set_llm_model(...) before get_llm().")
    if _LLM_INSTANCE is None:
        _LLM_INSTANCE = ChatOpenAI(model=_LLM_MODEL) #removed temperature.
    return _LLM_INSTANCE


#dynamic implementation, say user wants groq over chatgpt


#Rate limits for LLM API calls 

async def ainvoke_with_backoff(runnable, *args, max_retries=8, base_delay=0.5, max_delay=10.0, jitter=0.2, **kwargs):
    """
    runnable: In this case our llm api call with .ainvoke()
    """
    for attempt in range(max_retries + 1):
        try:
            return await runnable.ainvoke(*args, **kwargs)
        except RateLimitError as e:
            if attempt == max_retries:
                raise

            delay = min(max_delay, base_delay * (2 ** attempt))
            delay = delay + random.uniform(0, jitter)
            await asyncio.sleep(delay)

        except (APITimeoutError, APIError) as e:
            if attempt == max_retries:
                raise

            delay = min(max_delay, base_delay * (2 ** attempt))
            delay = delay + random.uniform(0, jitter)
            await asyncio.sleep(delay)

            


