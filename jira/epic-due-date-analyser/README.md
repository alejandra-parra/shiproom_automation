# Jira Due Date Analysis Tool

A Python tool for analyzing due date shifts in Jira issues, specifically focused on Deliverables and Epics.

## Features

- Analyze due date shifts for Deliverables and Epics
- Track different start date scenarios
- Generate visualizations of due date changes
- Support for team-based filtering
- Configurable date ranges for analysis

## Prerequisites

- Python 3.11 or higher
- A Jira instance with API access
- Access credentials (email and API token)

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd JiraDueDateAnalysis
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install the package and its dependencies:
```bash
pip install -e .
```

## Configuration

1. Create a `.env` file in the project root with your Jira credentials:
```env
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your-api-token
JIRA_SERVER=https://your-instance.atlassian.net
```

Optional environment variables:
```env
JIRA_START_DATE_FIELD=customfield_11018
JIRA_EPIC_LINKS_FIELD=parent
DEFAULT_PROJECT_KEY=PROJ
DEFAULT_TEAM_LABEL=TeamName
DEFAULT_START_DATE=2024-11-01
DEFAULT_END_DATE=2025-01-31
```

## Usage

### Command Line Interface

Analyze deliverables for a specific project and team:
```bash
python -m jira_due_date_analysis analyze deliverables --project PROJ --team TeamName
```

Additional options:
```bash
--start-date YYYY-MM-DD    Start date for analysis
--end-date YYYY-MM-DD      End date for analysis
--scenario SCENARIO        Start date scenario (options: DELIVERABLE_START_DATE, 
                          EARLIEST_EPIC_START, FIRST_ISSUE_IN_PROGRESS)
--output-dir directory     Directory for saving visualization outputs
--verbose                  Enable verbose logging
--show-start-dates        Show all start date markers in visualization
```

Analyze epics:
```bash
python -m jira_due_date_analysis analyze epics --project PROJ --team TeamName
```

Single run
```bash
python3 -m venv venv
source venv/bin/activate 
python3 -m jira_due_date_analysis analyze deliverables --project TOL --team Tolkien --start-date 2025-03-01 --end-date 2025-04-01
python3 -m jira_due_date_analysis analyze deliverables --project CFISO --team Isotopes --start-date 2025-03-01 --end-date 2025-04-01
python3 -m jira_due_date_analysis analyze deliverables --project BBEE --team Bumblebee --start-date 2025-03-01 --end-date 2025-04-01
python3 -m jira_due_date_analysis analyze deliverables --project PIC --team Picard --start-date 2025-03-01 --end-date 2025-04-01


# Business Foundations
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/BizFoundations --project AHOY --team ahoy
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/BizFoundations --project MOI --team moi
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/BizFoundations --project HEJO --team hejo
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/BizFoundations --project UFO --team UI-Foundation

## project, team
AHOY ahoy
MOI moi
HEJO hejo
UFO UI-Foundation

# Infrastructure
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Infrastructure --project MEC --team Mechagodzilla
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Infrastructure --project MOGWAI --team Mogwai
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Infrastructure --project KRK --team Kraken

## project, team
MEC Mechagodzilla
MOGWAI Mogwai
KRK Kraken

# Studio
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Studio --project SPA --team Sparks
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Studio --project LUMOS --team Lumos

## project, team
SPA Sparks
LUMOS Lumos

# Content Platform
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/CP --project GROOT --team Groot
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/CP --project FUS --team Fusion
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/CP --project CAPI --team Capi
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/CP --project CSTORE --team Cstore

## project, team
GROOT Groot
FUS Fusion
CAPI Capi
CSTORE Cstore

# Ecosystem
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Ecosystem --project EXT --team Tundra
python3 -m jira_due_date_analysis analyze deliverables --start-date 2025-02-01 --end-date 2025-04-04 --output-dir output/Ecosystem --project INTEG --team Taiga

## project, team
EXT Tundra
INTEG Taiga
```

### Output

The tool generates:
- Chart visualizations saved to the specified output directory
- Console output with summary statistics
- Detailed logs if verbose mode is enabled

## Project Structure

```
JiraDueDateAnalysis/
├── src/
│   └── jira_due_date_analysis/
│       ├── __init__.py
│       ├── __main__.py
│       ├── analyzer.py
│       ├── base_analyzer.py
│       ├── config.py
│       ├── deliverable_analyzer.py
│       ├── epic_analyzer.py
│       ├── models.py
│       ├── utils.py
│       └── visualizer.py
├── tests/
├── .env
├── pyproject.toml
├── requirements.txt
└── setup.py
```

## Development

For development installation:
```bash
pip install -e ".[dev]"
```

Running tests:
```bash
pytest
```

## Troubleshooting

Common issues and solutions:

1. **Authentication Errors**
   - Verify your Jira credentials in the .env file
   - Ensure your API token has sufficient permissions

2. **No Data Found**
   - Check if the project key and team label exist in your Jira instance
   - Verify the date range contains data
   - Ensure you have access to the project

3. **Custom Field Errors**
   - Verify the custom field IDs match your Jira configuration
   - Check if the fields are available for your issue types

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your chosen license]