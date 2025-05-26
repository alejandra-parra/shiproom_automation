# Sprint Capacity Calculator

A Flask web application that calculates engineering team capacity for sprint planning by integrating data from multiple sources:

- **Workday API**: Fetches logged absences and time-off requests
- **PagerDuty API**: Identifies on-call duties and support responsibilities  
- **Public Holiday API**: Determines holidays based on team member locations
- **Manual Status Updates**: Allows real-time status adjustments

The application generates a comprehensive calendar view showing each team member's availability status for each day of a specified time period.

![Sprint Capacity Calculator Screenshot](docs/images/sprint_capacity_calculator.png)
*Example sprint calendar showing team availability with color-coded statuses*

## Features

- 📅 **Sprint Calendar Generation**: Visual calendar showing team availability
- 🌍 **Multi-location Support**: Handles distributed teams across different countries/regions
- 📊 **Capacity Calculation**: Tracks individual capacity points and availability
- 🔄 **Real-time Updates**: Manual status overrides and adjustments

- ⏰ **Part-time Support**: Configurable non-working days for team members

## Prerequisites

- Python 3.8 or higher
- Access to the following APIs:
  - Workday API (for absence data)
  - PagerDuty API (for on-call schedules)
  

## Installation

1. **Navigate to the Sprint Capacity Calculator**
   ```bash
   cd SprintCapacityCalculator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root with the following variables:

   ```env
   # Workday API Configuration
   WORKDAY_TIMEOFF_URL=https://your-workday-instance.com/api/timeoff?start_date={start_date}&end_date={end_date}
   WORKDAY_USERNAME=your_workday_username
   WORKDAY_PASSWORD=your_workday_password

   # PagerDuty API Configuration
   PD_API_KEY=your_pagerduty_api_key
   PD_SCHEDULE_ID=your_pagerduty_schedule_id


   ```

## Configuration

### Team Configuration

Edit the `TEAM_DATA` dictionary in `config.py` to match your team:

```python
TEAM_DATA = {
    'Team Member Name': {
        'capacity': 10,           # Daily capacity points (8-10 typical)
        'location': 'GB-EN',      # Country-Region code for holidays
        'nonwork': ['fri'],       # Optional: non-working days for part-time
        'statuses': {}            # Auto-managed status tracking
    },
    # Add more team members...
}
```

#### Location Codes
Use ISO country codes with optional region suffixes:
- `GB-EN`: United Kingdom - England
- `DE-BY`: Germany - Bavaria  
- `DE-BE`: Germany - Berlin
- `US-CA`: United States - California
- `FR`: France (national holidays only)

#### Capacity Points
Typical values:
- `10`: Full-time (8 hours)
- `8`: Reduced capacity or part-time
- `6`: Significant part-time

### API Setup Instructions

#### Workday API
1. Contact Holli for access to credentials

#### PagerDuty API
1. Go to PagerDuty → Configuration → API Access
2. Create a new API key with read permissions
3. Find your schedule ID from the schedule URL or API
4. Add both values to your `.env` file



## Usage

1. **Start the application**
   
   **Option 1: Command line (recommended)**
   ```bash
   python run.py
   ```
   
   **Option 2: macOS double-click launcher**
   Double-click the `launch.command` file in Finder
   
   Both methods will:
   - Check your environment and dependencies
   - Start the Flask server on port 5001
   - Automatically open your browser to the application
   
   **Alternative: Direct start (requires activated virtual environment)**
   ```bash
   python app.py
   ```

2. **Access the web interface**
   
   The application will automatically open in your browser at `http://localhost:5001`

3. **Generate a sprint calendar**
   - Select start and end dates for your sprint
   - Click "Generate Calendar"
   - Review team availability and capacity

4. **Make manual adjustments**
   - Click on any cell to update a team member's status
   - Available statuses:
     - `Available`: Normal working capacity
     - `Planned Absence`: Pre-planned time off
     - `Unplanned Absence`: Sick leave or emergency absence
     - `Support`: On-call or support duties
     - `75% Available`: Partial availability
     - `50% Available`: Half-day availability
     - `25% Available`: Limited availability



## Status Definitions

The application uses color-coded statuses to provide a quick visual overview of team availability:

| Status | Description | Capacity Impact | Color |
|--------|-------------|-----------------|-------|
| Available | Normal working day | Full capacity | 🟢 Green |
| Planned Absence | Pre-planned time off | 0% capacity | 🟠 Orange |
| Unplanned Absence | Sick leave, emergency | 0% capacity | 🔴 Red |
| Support | On-call or support duty | Reduced capacity | 🔵 Blue |
| 75% Available | Minor conflicts/meetings | 75% capacity | 🟡 Yellow |
| 50% Available | Half-day availability | 50% capacity | 🟡 Yellow |
| 25% Available | Very limited availability | 25% capacity | 🟡 Yellow |
| Public Holiday | National/regional holiday | 0% capacity | 🟣 Purple |
| No Workday | Part-time non-working day | 0% capacity | ⚫ Gray |

The **Total Capacity** row at the bottom shows the aggregate capacity calculation for each day, helping you quickly identify potential bottlenecks or low-capacity days during sprint planning.

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   
   If you see "Address already in use" error:
   
   **Find what's using the port:**
   ```bash
   lsof -i :5001
   ```
   
   **Kill the process:**
   ```bash
   # Replace PID with the actual process ID from lsof output
   kill -9 PID
   ```
   
   **Or kill all Python processes (use with caution):**
   ```bash
   pkill -f python
   ```

2. **App Won't Stop (Ctrl+C doesn't work)**
   
   **Find the Flask process:**
   ```bash
   ps aux | grep python | grep app.py
   ```
   
   **Kill it:**
   ```bash
   kill -9 PID
   ```
   
   **Or find and kill by port:**
   ```bash
   lsof -ti:5001 | xargs kill -9
   ```

3. **Multiple Instances Running**
   
   **Kill all Flask/Python processes:**
   ```bash
   # List all Python processes
   ps aux | grep python
   
   # Kill specific Flask processes
   pkill -f "python.*app.py"
   pkill -f "python.*run.py"
   ```

4. **API Connection Errors**
   - Verify all API credentials in `.env` file
   - Check network connectivity and firewall settings
   - Ensure API endpoints are accessible

5. **Missing Team Members**
   - Ensure team member names match exactly between systems
   - Check that all team members are added to `TEAM_DATA`
   - Verify location codes are valid

6. **Holiday Data Issues**
   - Confirm location codes follow ISO standards
   - Check that the public holiday API is accessible
   - Verify date ranges don't span too many years

### Emergency Stop Commands

**Option 1: Use the kill script (easiest)**
```bash
./kill_app.sh
```

**Option 2: Manual commands**
```bash
# Kill by port (safest)
lsof -ti:5001 | xargs kill -9

# Kill by process name (more aggressive)
pkill -f "Sprint.*Calculator"
pkill -f "python.*run.py"
pkill -f "python.*app.py"
```

### Debug Mode

Run the application in debug mode for detailed error messages:

```bash
export FLASK_DEBUG=1  # On Windows: set FLASK_DEBUG=1
python3 app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Security Notes

- Never commit the `.env` file to version control
- Rotate API keys regularly
- Use least-privilege access for service accounts
- Monitor API usage and rate limits

## License

[Add your license information here]

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the application logs for error details
3. Contact your system administrator for API access issues
4. Create an issue in the repository for bugs or feature requests 