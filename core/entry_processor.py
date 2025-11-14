import traceback
from typing import Dict, Any

from common.logger import logger, log_entry_debug, log_entry_info, log_entry_error
from common import config
from common.models import AgentResult
from core.digest_generator import save_summary
from core.entry_filter import filter_entry, filter_entry_by_agent
from core.llm_client import get_completion
from core.content_helper import (
    to_markdown, 
    to_html, 
    parse_entry_content, 
    build_ordered_content
)


def process_entry(miniflux_client, entry: Dict[str, Any]) -> Dict[str, AgentResult]:
    """
    Process a single entry through all configured agents
    
    Args:
        miniflux_client: Miniflux client instance
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
            
            miniflux_client.update_entry(entry['id'], content=ordered_content)
            log_entry_info(entry, message=f"Updated successfully with new agent contents: {list(new_agent_contents.keys())}")
        else:
            log_entry_debug(entry, message="No new agent contents generated, entry unchanged")

        return new_agent_results
            
    except Exception as e:
        log_entry_error(entry, message=f"Processing failed: {e}")
        raise


def _process_entry_with_agents(entry: Dict[str, Any], agents: Dict[str, Any]) -> Dict[str, AgentResult]:
    """
    Process entry through all applicable agents
    
    Args:
        entry: Entry dictionary to process
        agents: Dictionary of agent_name: agent_config
        
    Returns:
        Dictionary of agent_name: agent_result
    """
    if not agents or not filter_entry(entry):
        return {}

    log_entry_debug(entry, message=f"Processing entry with agents: {list(agents.keys())}")
    log_entry_debug(entry, message="Processing entry content", include_title=False, include_content=True)

    agent_results: Dict[str, AgentResult] = {}
    # config.agents is ordered, required Python 3.7+
    for agent_name, agent_config in agents.items():
        agent_results[agent_name] = _process_with_single_agent((agent_name, agent_config), entry)
            
    return agent_results


def _process_with_single_agent(agent: tuple, entry: Dict[str, Any]) -> AgentResult:
    """
    Process entry with a single agent
    
    Args:
        agent: Tuple of (agent_name, agent_config)
        entry: Entry dictionary to process
        
    Returns:
        AgentResult with status and content/error
    """
    agent_name, agent_config = agent

    if not filter_entry_by_agent(agent, entry):
        log_entry_debug(entry, agent_name=agent_name, message="Filtered out")
        return AgentResult.filtered()

    log_entry_debug(entry, agent_name=agent_name, message="Starting processing")
    
    try:
        agent_content = _get_agent_content(agent, entry)
        log_entry_info(entry, agent_name=agent_name, message=f'Content: {agent_content}', include_title=True)

        if config.digest_schedule and agent_name == 'summary':
            # save summary to file for AI digest feature
            save_summary(entry, agent_content)

        formatted_content = _format_agent_content(agent_config, agent_content)
        log_entry_debug(entry, agent_name=agent_name, message=f"Formatted content: {formatted_content}", include_title=True)
        
        return AgentResult.success(formatted_content)     
    except Exception as e:
        log_entry_error(entry, agent_name=agent_name, message=f"Processing failed: {e}")
        logger.error(traceback.format_exc())
        return AgentResult.error(e, message=str(e))


def _get_agent_content(agent: tuple, entry: Dict[str, Any]) -> str:
    """
    Get processed content from LLM for a specific agent
    
    Args:
        agent: Tuple of (agent_name, agent_config)
        entry: Entry dictionary to process
        
    Returns:
        str: Processed content from LLM
    """
    agent_name, agent_config = agent
    title = entry['title']
    content_markdown = to_markdown(entry['content'])

    prompt_template = agent_config['prompt']
    prompt = prompt_template.replace('${title}', title).replace('${content}', content_markdown)

    if '${content}' in prompt_template:
        system_prompt = ""
        user_prompt = prompt
    else:
        system_prompt = prompt
        user_prompt = f"Process only the [Content]. The [Title] is for context.\n\n[Title]\n{title}\n\n[Content]\n{content_markdown}"

    log_entry_debug(entry, agent_name=agent_name, message=f"LLM request sent: system_prompt: {system_prompt}; user_prompt: {user_prompt}")

    agent_content = get_completion(system_prompt, user_prompt)
    
    log_entry_debug(entry, agent_name=agent_name, message=f"LLM response received: {agent_content}")
    return agent_content


def _format_agent_content(agent_config: Dict[str, Any], agent_content: str) -> str:
    """
    Format agent content based on style configuration
    
    Args:
        agent_config: Agent configuration dictionary
        agent_content: Raw content from LLM
        
    Returns:
        Formatted content string
    """
    template = agent_config.get('template', '')
    html_content = to_html(agent_content)
    
    if template:
        return template.replace('${content}', html_content)
    else:
        return html_content
