# Changelog

All notable changes to the Jira Issues Status Report Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [jira-issues-shiproom v2.0.0] - Released
### Changed
- Report name, Jira Issues Status Report Generator
- Deprecated Jellyfish as data source, we use Jira exclusively via two separate API calls
- Due date history only includes last change and current date for deliverables and last three changes and current date for epics; past dates are striken on the slide 
- Overdue logic is immediately overdue when due date is in the past (no automatic grace period)


### Added
- A duplicate of the report prior to update is being produced with every run
- Team ownership of the deliverables is now determined through a calculation of the team's share of its child epics
- Maturity field is being extracted from Jira 

### Fixed
- Fixed duplicate due dates appearing in slides when the change was only a formatting difference

## [jellyfish-shiproom v1.1.0] - Unreleased

### Added
- Enhanced due date history tracking with "In Progress" filtering
- 2-week grace period for overdue status (items only marked red if 2+ weeks past due)
- Only consider the last due date set on the same day (to filter out unintended dates)

### Changed
- **BREAKING**: Due date history now only includes changes that happened after the item was moved to "In Progress" status
- **BREAKING**: Overdue logic now requires items to be 2+ weeks past due (instead of immediately overdue)
- Enhanced due date deduplication logic to handle date format variations
- Improved status determination logic for more accurate red/yellow/green statuses

### Fixed
- Fixed duplicate due dates appearing in slides when original and current due dates are the same
- Fixed incorrect due date history filtering that was including changes before "In Progress"
- Fixed daily deduplication logic to properly keep the latest change per day
- Fixed date comparison logic to handle different date formats consistently

### Technical Improvements
- Added comprehensive debug logging for due date history processing
- Improved error handling for date parsing and comparison
- Enhanced code documentation and comments
- Better separation of concerns in due date processing logic

## [jellyfish-shiproom v1.0.0] - 2025-01-XX

### Added
- Initial release of Jellyfish Status Report Generator
- Google Slides integration for status reports
- Jira API integration for due date history
- Jellyfish API integration for work item data
- Automated status determination (Done/In Progress/Overdue)
- Due date history tracking with strikethrough formatting
- Team-specific configuration support
- Weekly lookback period filtering
- Investment classification filtering (Roadmap items only)

### Features
- Generates weekly status reports for engineering teams
- Shows due date history with visual formatting
- Color-coded status indicators (green/yellow/red)
- Hyperlinked issue keys in reports
- Configurable team settings
- Automated Google Slides updates 