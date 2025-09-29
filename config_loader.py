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
def get_team_ids(team_config: Dict[str, Any]) -> list[str]:
    """
    Normalize Jellyfish team IDs from config into a non-empty list of strings.
    This allows to trace back the issues if one team is working on multiple workstreams/projects in Jellyfish.
    Supports either:
      - team_ids: [123, 456]
      - team_id: 123   (legacy)
    """
    ids = team_config.get("team_ids")
    if ids is None:
        legacy = team_config.get("team_id")
        if legacy is not None:
            ids = [legacy]
        else:
            ids = []

    # Normalize to list[str]
    if isinstance(ids, (str, int)):
        ids = [ids]
    ids = [str(x).strip() for x in ids if x is not None and str(x).strip() != ""]
    return ids

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
    ids = get_team_ids(team_config)
    if not ids:
        print(
            f"Warning: Team {team_identifier} must define one or more 'team_id' "
            f"(or legacy 'team_id')"
        )
        return False

    # If your pipeline STILL relies on jira_project_key somewhere, keep a soft check:
    if "jira_project_key" in team_config and not team_config.get("jira_project_key"):
        print(f"Warning: Team {team_identifier} has empty jira_project_key")
        # Do not return False — make it a soft warning to keep compatibility.

    return True