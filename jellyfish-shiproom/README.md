# Jellyfish Status Report Generator - Google Slides Edition

This script generates status reports from Jellyfish data and writes them to Google Slides presentations. It creates formatted tables with deliverables and epics, including their status, maturity, and other relevant information.

## Project Structure

```
.
├── jellyfish_status_report.py  # Main script
├── config.yaml                 # Configuration file
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not in git)
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Service Account Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Slides API
4. Create a Service Account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Give it a name and description
   - Download the JSON key file
5. Share your Google Slides presentation with the service account email address (with Editor permissions)

### 2.1. Service Account JSON Formatting

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

### 4. Configuration File

Create a minimal `config.yaml` file. Most credentials are now in the `.env` file:

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
python jellyfish_status_report.py --config config.yaml
```

### Test Authentication

```bash
python jellyfish_status_report.py --config config.yaml --test-auth
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