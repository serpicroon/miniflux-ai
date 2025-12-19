import sys
import inspect
from typing import Dict
from yaml import safe_load

from common.models import Agent

class Config:
    def __init__(self):
        with open('config.yml', encoding='utf8') as f:
            self.c = safe_load(f)
        
        self.log_level = self.c.get('log_level', 'INFO')
        self.entry_since = self.c.get('entry_since', 0)

        self.miniflux_base_url = self._get_config_value('miniflux', 'base_url', None)
        self.miniflux_api_key = self._get_config_value('miniflux', 'api_key', None)
        self.miniflux_webhook_secret = self._get_config_value('miniflux', 'webhook_secret', None)

        self.llm_base_url = self._get_config_value('llm', 'base_url', None)
        self.llm_api_key = self._get_config_value('llm', 'api_key', None)
        self.llm_model = self._get_config_value('llm', 'model', None)
        self.llm_timeout = self._get_config_value('llm', 'timeout', 60)
        self.llm_max_workers = self._get_config_value('llm', 'max_workers', 4)
        self.llm_RPM = self._get_config_value('llm', 'RPM', 1000)

        self.digest_name = self._get_config_value('digest', 'name', "֎Minifluxᴬᴵ Digest for you")
        self.digest_url = self._get_config_value('digest', 'url', None)
        self.digest_entry_url = self._get_config_value('digest', 'entry_url', None)
        self.digest_schedule = self._get_config_value('digest', 'schedule', None)
        self.digest_prompts = self._get_config_value('digest', 'prompts', None)

        self.agents = self._load_agents()
        
        self._validate_config_compatibility()

    def _get_config_value(self, section, key, default=None):
        return self.c.get(section, {}).get(key, default)
    
    def _load_agents(self) -> Dict[str, Agent]:
        """
        Load agent configurations from YAML.
        
        Returns:
            Dictionary mapping agent names to Agent instances
        """
        agents_config = self.c.get('agents', {})
        agents = {}
        
        for agent_name, agent_config in agents_config.items():
            if not isinstance(agent_config, dict):
                continue
            
            agents[agent_name] = Agent(
                prompt=agent_config.get('prompt', ''),
                template=agent_config.get('template', ''),
                allow_rules=agent_config.get('allow_rules', []),
                deny_rules=agent_config.get('deny_rules', [])
            )
        
        return agents
    
    def _validate_config_compatibility(self):
        """
        Validate config file version compatibility.
        Check for deprecated fields and outdated formats.
        """
        if not self.c.get('agents'):
            return
        
        agents_config = self.c.get('agents', {})
        deprecated_field_agents = []
        
        for agent_name, agent_config in agents_config.items():
            if not isinstance(agent_config, dict):
                continue
            
            # Check for all deprecated fields
            deprecated_fields = []
            if 'title' in agent_config and 'style_block' in agent_config:
                deprecated_fields.extend(['title', 'style_block'])
            if 'allow_list' in agent_config:
                deprecated_fields.append('allow_list')
            if 'deny_list' in agent_config:
                deprecated_fields.append('deny_list')
            if 'min_content_length' in agent_config:
                deprecated_fields.append('min_content_length')
            
            if deprecated_fields:
                deprecated_field_agents.append(f"{agent_name} ({', '.join(deprecated_fields)})")
        
        # Report errors
        if deprecated_field_agents:
            agents_list = '\n'.join(f"  - {agent}" for agent in deprecated_field_agents)
            error_message = inspect.cleandoc(f"""
            ⚠️  Config Incompatibility Detected!
            
            Your config.yml uses deprecated fields that are no longer supported.
            Detected:
            {agents_list}
            
            For migration guide and examples, visit:
            https://github.com/serpicroon/miniflux-ai
            """)
            
            print(error_message)
            sys.exit(1)


config = Config()