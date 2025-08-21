# Jellyfish Status Report Generator - Google Slides Edition

This script generates status reports from Jellyfish data and writes them to Google Slides presentations. It creates formatted tables with deliverables and epics, including their status, maturity, and other relevant information.

📋 **[Changelog](CHANGELOG.md)** - See what's new and what's changed

## 🚀 Quick Start

If you're switching between different projects in this repository, here's how to get this project running:

```bash
# 1. Navigate to this project directory
cd jellyfish-shiproom

# 2. Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Run the script
python jellyfish_status_report.py --config config.yaml
```

**Note:** This project uses a `.venv` virtual environment (not `venv`). Make sure you're activating the correct one!

## Project Structure

```
jellyfish-shiproom/
├── jellyfish_status_report.py  # Main script
├── config.yaml                 # Configuration file
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git)
├── .venv/                     # Virtual environment (use this one!)
├── venv/                      # Old virtual environment (ignore)
├── clients/                   # API client modules
├── config/                    # Configuration utilities
├── utils/                     # Utility functions
├── logs/                      # Log files
└── README.md                 # This file
```

## Setup

### 1. Virtual Environment Setup

This project uses a `.venv` virtual environment. If you need to create a new one:

```bash
# Create new virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Dependencies

```bash
# Make sure your virtual environment is activated
source .venv/bin/activate

# Install all required packages
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Google Service Account Configuration
# Option 1: Path to JSON file
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/your/service-account-key.json

# Option 2: JSON content directly (recommended for deployment)
# GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project",...}'

# Jellyfish API Configuration
JELLYFISH_BASE_URL=https://app.jellyfish.co/endpoints/export/v0
JELLYFISH_API_KEY=your-jellyfish-api-key-here

# Jira API Configuration (Optional - for due date history)
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@domain.com
JIRA_API_TOKEN=your-jira-api-token
```

### 4. Google Service Account Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Slides API
4. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Give it a name and description
   - Download the JSON key file
5. Share your Google Slides presentation with the service account email address (with Editor permissions)

### 4.1. Service Account JSON Formatting

You have two options for providing the service account credentials:

**Option 1: File Path (simpler for local development)**
```bash
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/your/service-account-key.json
```

**Option 2: JSON Content (recommended for deployment/CI/CD)**
```bash
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project-id","private_key_id":"key-id","private_key":"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n","client_email":"your-service-account@your-project.iam.gserviceaccount.com","client_id":"123456789","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"}'
```

**Important formatting notes for Option 2:**
- Wrap the entire JSON in single quotes (`'...'`)
- Keep all the JSON on one line (no line breaks)
- The private key will contain `\n` characters - keep these as-is
- Don't escape the quotes inside the JSON when using single quotes outside

**Quick conversion from file to environment variable:**
```bash
# On macOS/Linux, you can convert your JSON file to a one-liner:
cat your-service-account.json | tr -d '\n' | sed "s/'/\\\'/g"

# Then copy the output and wrap it in single quotes in your .env file:
# GOOGLE_SERVICE_ACCOUNT_JSON='paste-the-output-here'
```

### 5. Configuration File

The `config.yaml` file is already configured for Team Tolkien. Update it if needed:

```yaml
# Configuration file - credentials come from environment variables
# Non-sensitive configuration goes here

# Required: Google Slides presentation to update
google_slides:
  presentation_id: "your-presentation-id-here"
  slide_id: "your-slide-id-here"

# Required: Team configuration
team:
  team_id: "your-team-id"
  team_name: "Your Team Name"
```

**Note:** To find your Google Presentation ID and Slide ID:

**Presentation ID:**
- Open your Google Slides presentation
- Look at the URL: `https://docs.google.com/presentation/d/1ABC123DEF456/edit`
- The presentation ID is: `1ABC123DEF456`

**Slide ID:**
- Navigate to the specific slide you want to update
- Look at the URL: `https://docs.google.com/presentation/d/1ABC123DEF456/edit#slide=id.g789XYZ123_0_0`
- The slide ID is: `g789XYZ123_0_0` (everything after `slide=id.`)
- Alternatively, right-click on the slide thumbnail in the left panel and select "Copy link" - the slide ID will be in that URL

**Important:** All credentials (API keys, tokens, passwords) MUST be in the `.env` file. The config file is only for non-sensitive configuration like team IDs and presentation IDs.

## Usage

### Generate Status Report

```bash
# Make sure you're in the jellyfish-shiproom directory
cd jellyfish-shiproom

# Activate virtual environment
source .venv/bin/activate

# Run the script for ALL teams (default behaviour if not specified)
python jellyfish_status_report.py --config config.yaml --team all

# Run the script for a SINGLE team (only that slide is updated)
python jellyfish_status_report.py --config config.yaml --team TOL

# You can also omit --team to fall back to whatever is set in config / defaults to all
python jellyfish_status_report.py --config config.yaml
```

### Team Selection Logic

The script now supports generating slides for either:

1. A single team (only that team's slide is cleared and re-generated)
2. All teams listed in `teams_config.yaml`

Selection priority (highest wins):
1. `--team` CLI argument
2. `team_selection` key in `config.yaml` (optional)
3. Fallback default: `all`

Valid values for `--team` / `team_selection`:
- `all` – process every configured team
- A team identifier key from `teams_config.yaml` (e.g. `BBEE`, `TOL`, `CLIP`, etc.)

If you pass a team identifier that does not exist, the script will list all available keys.

### Required Supporting File: `teams_config.yaml`

Multi-team execution depends on `teams_config.yaml`, which defines each team's mapping:

```yaml
teams:
   TOL:
      jira_project_key: "TOL"
      team_name: "[PRD] Tolkien: [TOL]"
      team_id: 44743
      slide_id: "id.slide_20250719_151730"   # Optional – strip leading 'id.' automatically
      presenter: ""                           # Optional metadata
      image_link: ""                          # Optional metadata
```

Fields:
- `jira_project_key` (required)
- `team_name` (required)
- `team_id` (required – Jellyfish team ID)
- `slide_id` (optional) If missing or invalid the script creates a new slide and prints its ID
- `presenter`, `image_link` (optional)

Validation: A team missing any required field or with an empty `jira_project_key` is skipped.

### How Slides Are Updated

For each selected team:
1. Existing slide content is cleared (if `slide_id` exists and slide is found)
2. If the slide does not exist or no `slide_id` is configured, a new blank slide is created and its new ID is printed (copy it back into `teams_config.yaml` for future runs)
3. Deliverables and epics are fetched for the date range
4. Each item is enriched with Jira due date history + labels (if available)
5. Items are filtered based on lookback logic; excluded items are added off-canvas for traceability
6. A merged table plus a Risks / Mitigations box is rendered

### Example Workflows

Update only Tolkien:
```bash
python jellyfish_status_report.py --config config.yaml --team TOL
```

Regenerate every team slide:
```bash
python jellyfish_status_report.py --config config.yaml --team all
```

Run using `team_selection` specified in `config.yaml` (e.g. set `team_selection: CLIP`):
```bash
python jellyfish_status_report.py --config config.yaml
```

### Adding a New Team
1. Add an entry under `teams:` in `teams_config.yaml` with required fields
2. (Optional) Leave out `slide_id` on the first run – the script will create a slide and print the new ID
3. Re-run after copying the printed slide ID into the config for stable updates

### Troubleshooting Team Runs
- Slide not cleared: Ensure the `slide_id` matches the actual Google Slides object ID (remove any duplicated `id.` prefix; the script strips one automatically)
- New slide created every run: You forgot to add / persist the created `slide_id` back into `teams_config.yaml`
- Team skipped: Check logs for missing required field warning
- No items shown: Confirm Jellyfish team ID is correct and date range has data

### Verify Setup

The script will output detailed information about:
- API connections (Jellyfish, Jira, Google Slides)
- Data fetching and processing
- Table generation in Google Slides

If everything is working, you should see:
- "Report generated in Google Slides" at the end
- No error messages
- Detailed logging of the process

## Changelog Management

This project maintains a detailed changelog to track all changes and improvements. The changelog follows the [Keep a Changelog](https://keepachangelog.com/) format.

### Adding New Entries

Use the helper script to easily add new changelog entries:

```bash
# Add a new feature
python scripts/update_changelog.py --type added --message "New feature description"

# Fix a bug
python scripts/update_changelog.py --type fixed --message "Fixed issue with date parsing"

# Change existing functionality
python scripts/update_changelog.py --type changed --message "Updated overdue logic to use 2-week grace period"

# Remove deprecated feature
python scripts/update_changelog.py --type removed --message "Removed deprecated API endpoint"
```

### Available Change Types

- `added` - New features
- `changed` - Changes to existing functionality
- `deprecated` - Soon-to-be removed features
- `removed` - Removed features
- `fixed` - Bug fixes
- `security` - Security-related changes

### Version Management

Since this is one feature folder in a larger repository, versioning is scoped to this feature:

1. Update the version number in the changelog (e.g., `jellyfish-shiproom v1.1.0`)
2. Move entries from the current version to a new version when ready
3. Add a release date
4. Optionally tag the release in git with feature prefix

Example:
```bash
# Create a feature-specific version tag
git tag -a jellyfish-shiproom-v1.1.0 -m "Jellyfish Status Report v1.1.0"
git push origin jellyfish-shiproom-v1.1.0
```

### Multi-Project Repository Notes

This changelog tracks changes specific to the jellyfish-shiproom feature. Other features in this repository may have their own changelogs or use a different versioning strategy.

## Troubleshooting

### Common Issues

1. **Wrong Virtual Environment**: Make sure you're using `.venv`, not `venv`
   ```bash
   # Check which Python you're using
   which python
   # Should show: /path/to/jellyfish-shiproom/.venv/bin/python
   ```

2. **Missing Dependencies**: If you get import errors
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Environment Variables**: Make sure your `.env` file exists and has the correct values
   ```bash
   # Check if .env file exists
   ls -la .env
   ```

4. **API Permissions**: Ensure your service account has access to the Google Slides presentation

### Switching Between Projects

When switching between different projects in this repository:

```bash
# Deactivate current environment (if any)
deactivate

# Navigate to the jellyfish-shiproom project
cd jellyfish-shiproom

# Activate this project's environment
source .venv/bin/activate

# Verify you're in the right environment
which python
# Should show: .../jellyfish-shiproom/.venv/bin/python
```

## Features

- Fetches deliverables and epics from Jellyfish API
- Integrates with Jira to get due date history
- Creates formatted tables in Google Slides
- Color-codes status (Done, In Progress, Overdue)
- Automatically positions content on slides
- Supports both file-based and JSON-based Google Service Account authentication
- Configurable through environment variables and YAML config

## Required Permissions

- Google Slides API access
- Editor access to the target Google Slides presentation
- Jellyfish API access
- Jira API access (optional, for due date history)

## Security Notes

- All sensitive credentials are stored in the `.env` file
- The `.env` file should never be committed to version control
- Add `.env` to your `.gitignore` file
- Environment variables take precedence over config file values
- The config file can be used for non-sensitive overrides

## Development

### Setting Up Development Environment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/jellyfish-status-report.git
cd jellyfish-status-report
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
```

### Running Tests

Currently, the project includes basic authentication testing:
```bash
python jellyfish_status_report.py --config config.yaml --test-auth
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and small
- Use type hints where possible

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Jellyfish API for providing the data
- Google Slides API for presentation generation
- Jira API for additional metadata 