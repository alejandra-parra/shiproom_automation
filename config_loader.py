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
def get_project_keys(team_config: Dict[str, Any]) -> list[str]:
    """
    Normalize Jira project keys from config into a non-empty list of strings.
    This allows to trace back the issues if one team is working on multiple workstreams/projects.

    """
    jira_keys = team_config.get("jira_project_keys")
    if jira_keys is None:
        legacy = team_config.get("jira_project_key")
        if legacy is not None:
            jira_keys = [legacy]
        else:
            jira_keys = []

    # Normalize to list[str]
    if isinstance(jira_keys, (str, int)):
        jira_keys= [jira_keys]
    jira_keys = [str(x).strip() for x in jira_keys if x is not None and str(x).strip() != ""]
    return jira_keys

def validate_team_config(team_config: Dict[str, Any], team_identifier: str) -> bool:
    """
    Validate that a team configuration has all required fields.

    Requirements:
      - team_name (always)
      - EITHER team_ids (list) OR team_id (single, legacy)

    jira_project_key is optional now (only if some other parts still use it).
    """
    # team_name is always required
    if "team_name" not in team_config:
        print(f"Warning: Team {team_identifier} missing required field 'team_name'")
        return False

    # Normalize and check Jellyfish team IDs
    jira_keys = get_project_keys(team_config)
    if not jira_keys:
        print(
            f"Warning: Team {team_identifier} must define one or more 'jira_project_keys' "
            f"(or legacy 'jira_project_key')"
        )
        return False

    # If your pipeline STILL relies on jira_project_key somewhere, keep a soft check:
    if "jira_project_key" in team_config and not team_config.get("jira_project_key"):
        print(f"Warning: Team {team_identifier} has empty jira_project_key")
        # Do not return False — make it a soft warning to keep compatibility.

    return True