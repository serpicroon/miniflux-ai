class LLMResponseError(Exception):
    """
    Raised when the LLM returns an invalid, empty, or unexpected response.
    This indicates a contract violation by the LLM or its SDK.
    """