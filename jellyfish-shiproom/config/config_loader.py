"""
Configuration loader for the Jellyfish Status Report Generator
"""

import yaml
from typing import Dict, List, Optional, Any, cast
from pathlib import Path

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
            return {}
        if isinstance(config, dict):
            return cast(Dict[str, Any], config)
        else:
            print(f"Warning: Config file {config_path} did not contain a dictionary, returning empty dict")
            return {}
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        raise

def load_teams_config(teams_config_path: str) -> Dict[str, Any]:
    """Load teams configuration from a YAML file"""
    try:
        with open(teams_config_path, 'r') as f:
            teams_config = yaml.safe_load(f)
        if teams_config is None:
            return {}
        if isinstance(teams_config, dict):
            return cast(Dict[str, Any], teams_config)
        else:
            print(f"Warning: Teams config file {teams_config_path} did not contain a dictionary, returning empty dict")
            return {}
    except Exception as e:
        print(f"Error loading teams config file {teams_config_path}: {e}")
        raise

def get_team_config(teams_config: Dict[str, Any], team_identifier: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific team by identifier"""
    teams = teams_config.get('teams', {})
    return teams.get(team_identifier)

def get_all_teams(teams_config: Dict[str, Any]) -> List[tuple[str, Dict[str, Any]]]:
    """Get all teams with their identifiers"""
    teams = teams_config.get('teams', {})
    return [(identifier, team_config) for identifier, team_config in teams.items()]

def validate_team_config(team_config: Dict[str, Any], team_identifier: str) -> bool:
    """Validate that a team configuration has all required fields"""
    required_fields = ['jira_project_key', 'team_name', 'team_id']
    
    for field in required_fields:
        if field not in team_config:
            print(f"Warning: Team {team_identifier} missing required field '{field}'")
            return False
    
    # Check if team has a valid project key (not empty)
    if not team_config.get('jira_project_key'):
        print(f"Warning: Team {team_identifier} has empty jira_project_key - skipping")
        return False
    
    return True 