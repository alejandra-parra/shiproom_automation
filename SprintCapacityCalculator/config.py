from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Tolkien Sprint Application"""
    
    # Workday API Configuration
    WORKDAY_TIMEOFF_URL = os.getenv('WORKDAY_TIMEOFF_URL')
    WORKDAY_USERNAME = os.getenv('WORKDAY_USERNAME')
    WORKDAY_PASSWORD = os.getenv('WORKDAY_PASSWORD')
    
    # PagerDuty API Configuration
    PD_API_KEY = os.getenv('PD_API_KEY')
    PD_SCHEDULE_ID = os.getenv('PD_SCHEDULE_ID')
    

    
    # Team Configuration
    # 
    # ⚠️  ENGINEERING MANAGERS: UPDATE THIS SECTION FOR YOUR TEAM
    # 
    # Each team member should have:
    # - capacity: Daily capacity points (typically 8-10)
    # - location: Country-Region code (e.g., 'GB-EN', 'DE-BY', 'DE-BE')
    # - nonwork: List of non-working days (optional, e.g., ['fri'] for part-time)
    # - statuses: Dictionary for tracking daily statuses (automatically managed)
    #
    # Example team member entry:
    # 'Full Name': {
    #     'capacity': 10,           # Daily story points capacity
    #     'location': 'US-CA',      # Country-Region for holiday calculation
    #     'nonwork': ['fri'],       # Optional: non-working days
    #     'statuses': {}            # Leave empty - managed automatically
    # }
    TEAM_DATA = {
        'Ahmed Tajelsir': {
            'capacity': 10, 
            'location': 'GB-EN', 
            'statuses': {}
        },
        'Aodhagan Murphy': {
            'capacity': 10, 
            'location': 'GB-EN', 
            'statuses': {}
        },
        'Chris Helgert': {
            'capacity': 10, 
            'location': 'DE-BY', 
            'statuses': {}
        },
        'Kudakwashe Mupeni': {
            'capacity': 10, 
            'location': 'DE-BE', 
            'statuses': {}
        },
        'Maya Gillilan': {
            'capacity': 8, 
            'location': 'DE-BE', 
            'nonwork': ['fri'], 
            'statuses': {}
        },
        'Yuri Mazursky': {
            'capacity': 10, 
            'location': 'GB-EN', 
            'statuses': {}
        },
        'Yves Rijckaert': {
            'capacity': 10, 
            'location': 'DE-BE', 
            'statuses': {}
        }
    }
    
