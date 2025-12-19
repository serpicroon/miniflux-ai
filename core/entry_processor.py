import traceback
import threading
from typing import Dict, Any
from cachetools import TTLCache

from common.logger import logger, log_entry_debug, log_entry_info, log_entry_error
from common import config
from common.models import AgentResult, Agent
from core.digest_generator import save_summary
from core.rule_matcher import match_rules
from core.llm_client import get_completion
from core.miniflux_client import get_miniflux_client
from core.content_helper import (
    to_markdown, 
    to_html, 
    parse_entry_content, 
    build_ordered_content
)

# Entry processing cache to avoid duplicate processing
_ENTRY_CACHE_LOCK = threading.Lock()
_ENTRY_CACHE = TTLCache[int, bool](maxsize=1000, ttl=300)


def process_entry(entry: Dict[str, Any]) -> Dict[str, AgentResult]:
    """
    Process a single entry through all configured agents
    
    Args:
        entry: Entry dictionary to process
    
    Returns:
        Dictionary of agent_name: agent_result
    """
    try:
        log_entry_debug(entry, message="Starting processing")
        
        # Parse entry content once to get original content and existing agent results
        original_content, existing_agent_contents = parse_entry_content(entry['content'])

        if not original_content.strip():
            log_entry_debug(entry, message="Entry content is empty, skipping")
            return {}
        
        original_entry = entry.copy()
        original_entry['content'] = original_content
        
        if existing_agent_contents:
            log_entry_debug(original_entry, message=f"Found existing agent contents: {list(existing_agent_contents.keys())}")
        
        # process entry with config.agents excluding keys in existing agent contents
        new_agents = {k: v for k, v in config.agents.items() if k not in existing_agent_contents.keys()}
        new_agent_results = _process_entry_with_agents(original_entry, new_agents)
        new_agent_contents = {k: v.content for k, v in new_agent_results.items() if v.is_success}

        if new_agent_contents:
            # Combine existing and new agent contents, then update entry
            all_agent_contents = {**existing_agent_contents, **new_agent_contents}
            ordered_content = build_ordered_content(all_agent_contents, original_content)
            
            get_miniflux_client().update_entry(entry['id'], content=ordered_content)
            log_entry_info(entry, message=f"Updated successfully with new agent contents: {list(new_agent_contents.keys())}")
        else:
            log_entry_debug(entry, message="No new agent contents generated, entry unchanged")

        return new_agent_results
            
    except Exception as e:
        log_entry_error(entry, message=f"Processing failed: {e}")
        raise


def _process_entry_with_agents(entry: Dict[str, Any], agents: Dict[str, Agent]) -> Dict[str, AgentResult]:
    """
    Process entry through all applicable agents
    
    Args:
        entry: Entry dictionary to process
        agents: Dictionary of agent_name: Agent dataclass
        
    Returns:
        Dictionary of agent_name: agent_result
    """
    if not agents:
        return {}
    
    # Check if entry was already processed (cache check)
    entry_id = entry['id']
    with _ENTRY_CACHE_LOCK:
        if entry_id in _ENTRY_CACHE:
            log_entry_debug(entry, message="Entry already processed (cache hit), skipping")
            return {}
        _ENTRY_CACHE[entry_id] = True

    log_entry_debug(entry, message=f"Processing entry with agents: {list(agents.keys())}")
    log_entry_debug(entry, message="Processing entry content", include_title=False, include_content=True)

    agent_results: Dict[str, AgentResult] = {}
    # config.agents is ordered, required Python 3.7+
    for agent_name, agent in agents.items():
        agent_results[agent_name] = _process_with_single_agent(agent_name, agent, entry)
            
    return agent_results


def _process_with_single_agent(agent_name: str, agent: Agent, entry: Dict[str, Any]) -> AgentResult:
    """
    Process entry with a single agent
    
    Args:
        agent_name: Name of the agent
        agent: Agent dataclass instance
        entry: Entry dictionary to process
        
    Returns:
        AgentResult with status and content/error
    """
    # Check if entry matches agent's rules
    if not match_rules(entry, agent.allow_rules, agent.deny_rules):
        log_entry_debug(entry, agent_name=agent_name, message="Filtered out by rules")
        return AgentResult.filtered()

    log_entry_debug(entry, agent_name=agent_name, message="Starting processing")
    
    try:
        agent_content = _get_agent_content(agent_name, agent, entry)
        log_entry_info(entry, agent_name=agent_name, message=f'Content: {agent_content}', include_title=True)

        if config.digest_schedule and agent_name == 'summary':
            # save summary to file for AI digest feature
            save_summary(entry, agent_content)

        formatted_content = _format_agent_content(agent, agent_content)
        log_entry_debug(entry, agent_name=agent_name, message=f"Formatted content: {formatted_content}", include_title=True)
        
        return AgentResult.success(formatted_content)
    except ValueError as e:
        log_entry_error(entry, agent_name=agent_name, message=f"LLM error: {e}")
        return AgentResult.error(e, message=str(e))
    except Exception as e:
        log_entry_error(entry, agent_name=agent_name, message=f"Processing failed: {e}")
        logger.error(traceback.format_exc())
        return AgentResult.error(e, message=str(e))


def _get_agent_content(agent_name: str, agent: Agent, entry: Dict[str, Any]) -> str:
    """
    Get processed content from LLM for a specific agent
    
    Args:
        agent_name: Name of the agent
        agent: Agent dataclass instance
        entry: Entry dictionary to process
        
    Returns:
        str: Processed content from LLM
    """
    title = entry['title']
    content_markdown = to_markdown(entry['content'])

    prompt_template = agent.prompt
    prompt = prompt_template.replace('{title}', title).replace('{content}', content_markdown)

    if '{content}' in prompt_template:
        system_prompt = ""
        user_prompt = prompt
    else:
        system_prompt = prompt
        user_prompt = f"Process only the [Content]. The [Title] is for context.\n\n[Title]\n{title}\n\n[Content]\n{content_markdown}"

    log_entry_debug(entry, agent_name=agent_name, message=f"LLM request sent: system_prompt: {system_prompt}; user_prompt: {user_prompt}")

    agent_content = get_completion(system_prompt, user_prompt)
    
    log_entry_debug(entry, agent_name=agent_name, message=f"LLM response received: {agent_content}")
    return agent_content


def _format_agent_content(agent: Agent, agent_content: str) -> str:
    """
    Format agent content based on style configuration
    
    Args:
        agent: Agent dataclass instance
        agent_content: Raw content from LLM
        
    Returns:
        Formatted content string
    """
    template = agent.template
    html_content = to_html(agent_content)
    
    if template:
        return template.replace('{content}', html_content)
    else:
        return html_content
