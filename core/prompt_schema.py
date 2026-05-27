"""Prompt schema definitions — format descriptions, templates, and message processing."""

from dataclasses import dataclass
from string import Template


@dataclass(frozen=True)
class EntryPromptSchema:
    """Agent entry schema — format description and template are a coupled pair.

    The format_description tells the LLM about the data structure,
    while template renders the actual data. They must stay in sync.
    """

    format_description: str = (
        "<input_format>\n"
        "The input provides <title> and <content>.\n"
        "The <title> is for context only.\n"
        "The <content> is the data to process according to the instructions.\n"
        "</input_format>"
    )
    template: str = (
        "<entry>\n"
        "<title>\n"
        "$title\n"
        "</title>\n"
        "\n"
        "<content>\n"
        "$content\n"
        "</content>\n"
        "</entry>"
    )

    def render(self, title: str, content: str) -> str:
        """Render the entry template with the given title and content."""
        return Template(self.template).safe_substitute(title=title, content=content)


ENTRY_PROMPT_SCHEMA = EntryPromptSchema()


@dataclass(frozen=True)
class DigestPromptSchema:
    """Digest prompt schema — format descriptions for digest generation.

    These describe the data format and citation rules to the LLM.
    The user-configurable prompts (greeting, summary) live in YAML config.
    """

    input_format: str = (
        # [^ID] is concise — entries are referenced by ID multiple times
        # throughout a digest, so compact notation saves meaningful tokens.
        "<input_format>\n"
        "Each entry is prefixed with its unique ID: [^ID].\n"
        "For example: [^175799] Summary text.\n"
        "</input_format>"
    )
    citation_format: str = (
        "<citation_format>\n"
        "Always use [^ID] format for citations. "
        "Chain multiple sources without spaces: [^123][^456].\n"
        "Unless otherwise specified, append [^ID] directly after the relevant key point.\n"
        "</citation_format>"
    )
    citation_verification: str = (
        "<citation_verification>\n"
        "Before writing: check every [^ID] in your draft against the input.\n"
        "After writing: verify each [^ID] exists in the source data.\n"
        "</citation_verification>"
    )


DIGEST_PROMPT_SCHEMA = DigestPromptSchema()


def apply_prompt_processing(
    prompts: list[tuple[str, str]], mode: str
) -> list[dict[str, str]]:
    """Transform ordered prompt tuples into API messages per processing mode."""
    if mode == "none":
        return [{"role": r, "content": c} for r, c in prompts]
    if mode == "strict":
        # 1. merge consecutive same-role prompts
        merged: list[dict[str, str]] = []
        for role, content in prompts:
            if merged and merged[-1]["role"] == role:
                merged[-1]["content"] += "\n\n" + content
            else:
                merged.append({"role": role, "content": content})
        # 2. non-first system → user, wrapped in <instruction> to preserve weight
        for m in merged[1:]:
            if m["role"] == "system":
                m["role"] = "user"
                m["content"] = f"<instruction>\n{m['content']}\n</instruction>"
        # 3. re-merge consecutive same-role after demotion
        result: list[dict[str, str]] = []
        for m in merged:
            if result and result[-1]["role"] == m["role"]:
                result[-1]["content"] += "\n\n" + m["content"]
            else:
                result.append(m)
        return result
    if mode == "single":
        return [{"role": "user", "content": "\n\n".join(c for _, c in prompts)}]
