from common import config
from common.exceptions import LLMResponseError
from common.logger import get_logger
from core.prompt_schema import apply_prompt_processing
from openai import OpenAI
from ratelimit import limits, sleep_and_retry

logger = get_logger(__name__)

llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)


@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def chat_completion(
    prompts: list[tuple[str, str]], temperature: float | None = None, retries: int = 0
) -> str:
    for attempt in range(retries + 1):
        try:
            kwargs = {
                "model": config.llm_model,
                "timeout": config.llm_timeout,
                "messages": apply_prompt_processing(
                    prompts, config.llm_prompt_processing
                ),
            }

            if temperature is not None:
                kwargs["temperature"] = temperature

            completion = llm_client.chat.completions.create(**kwargs)
            logger.debug(f"LLM response: {completion}")

            if not completion.choices or not completion.choices[0].message:
                raise LLMResponseError(
                    f"LLM returned unexpected response: {completion}"
                )

            content = completion.choices[0].message.content
            if not content:
                raise LLMResponseError(f"LLM returned empty content: {completion}")

            return content.strip()
        except Exception:
            if attempt < retries:
                logger.warning(
                    "Chat completion failed, retrying (%d/%d)...",
                    attempt + 1,
                    retries,
                )
                continue
            raise
