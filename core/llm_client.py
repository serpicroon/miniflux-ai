from openai import OpenAI
from ratelimit import limits, sleep_and_retry
from common.logger import logger

from common import config

DEFAULT_SYSTEM_PROMPT = (
    "You are Miniflux AI Agent, skillfully interpreting RSS content "
    "to reframe its message with clarity and depth as requested."
)

llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)


@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def get_completion(system_prompt: str, user_prompt: str) -> str:
    """
    Get completion from LLM
    
    Args:
        system_prompt: System prompt for the LLM (if None or empty, uses default)
        user_prompt: User prompt for the LLM
        
    Returns:
        LLM response content
        
    Raises:
        ValueError: If LLM returns empty or invalid response
        Exception: If LLM API call fails
    """
    if not system_prompt or not system_prompt.strip():
        system_prompt = DEFAULT_SYSTEM_PROMPT
    
    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    completion = llm_client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        timeout=config.llm_timeout
    )
    logger.debug(f"LLM response: {completion}")
    
    if not completion.choices or not completion.choices[0].message:
        raise ValueError(f"LLM returned unexpected response: {completion}")
    
    content = completion.choices[0].message.content
    if not content:
        raise ValueError(f"LLM returned empty content: {completion}")
    
    return content.strip()
 
