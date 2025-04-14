"""Configuration management for the Jira Due Date Analysis tool.

This module handles all configuration settings for the application, including
Jira connection details and default analysis parameters.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables once at module level
load_dotenv()

class JiraFieldMappings:
    """Standard and custom Jira field mappings."""
    # Standard Jira fields
    DUE_DATE: str = 'duedate'
    SUMMARY: str = 'summary'
    STATUS: str = 'status'
    
    # Custom fields - override these via environment variables if needed
    START_DATE: str = 'customfield_11018'
    EPIC_LINKS: str = 'parent'

class JiraSettings(BaseSettings):
    """Jira connection and authentication settings."""
    email: str
    api_token: str
    server: str
    
    # Custom field mappings with defaults from JiraFieldMappings
    start_date_field: str = JiraFieldMappings.START_DATE
    epic_links_field: str = JiraFieldMappings.EPIC_LINKS
    due_date_field: str = JiraFieldMappings.DUE_DATE
    
    class Config:
        """Pydantic configuration."""
        env_prefix = 'JIRA_'
        case_sensitive = False
        
        # List of all environment variables this class expects
        env_file_encoding = 'utf-8'
        fields = {
            'email': {'env': 'JIRA_EMAIL'},
            'api_token': {'env': 'JIRA_API_TOKEN'},
            'server': {'env': 'JIRA_SERVER'},
            'start_date_field': {'env': 'JIRA_START_DATE_FIELD'},
            'epic_links_field': {'env': 'JIRA_EPIC_LINKS_FIELD'}
        }

class AnalysisSettings(BaseSettings):
    """Default analysis parameters and settings."""
    project_key: str = 'TOL'
    team_label: str = 'Tolkien'
    start_date: str = '2025-03-01'
    end_date: str = '2025-03-31'
    
    class Config:
        """Pydantic configuration."""
        env_prefix = 'DEFAULT_'
        case_sensitive = False
        
        # List of all environment variables this class expects
        fields = {
            'project_key': {'env': 'DEFAULT_PROJECT_KEY'},
            'team_label': {'env': 'DEFAULT_TEAM_LABEL'},
            'start_date': {'env': 'DEFAULT_START_DATE'},
            'end_date': {'env': 'DEFAULT_END_DATE'}
        }

# Create global instances
jira_settings = JiraSettings()
analysis_settings = AnalysisSettings()

# Type aliases for better code readability
JiraConfig = JiraSettings
AnalysisConfig = AnalysisSettings