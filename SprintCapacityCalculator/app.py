# app.py
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from config import Config

app = Flask(__name__)

# Global team data - loaded from config
team_data = Config.TEAM_DATA

# Workday Functions
def fetch_absence_data(start_date, end_date):
    start_date_str = start_date + "-07%3A00"
    end_date_str = end_date + "-07%3A00"
    
    url = Config.WORKDAY_TIMEOFF_URL.format(
        start_date=start_date_str, 
        end_date=end_date_str
    )
    
    response = requests.get(
        url, 
        auth=HTTPBasicAuth(Config.WORKDAY_USERNAME, Config.WORKDAY_PASSWORD)
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return None

def prepare_workday_absence_data(raw_absence_data, team_data, start_date):
    prepared_data = {}
    
    for entry in raw_absence_data.get('Report_Entry', []):
        worker_name = entry['worker']
        if worker_name in team_data:
            total_units = entry['Total_Units']
            unit_of_time = entry['unitOfTime']
            date = entry['date']
            entered_on = entry['Entered_On']
            
            status = get_absence_status(total_units, unit_of_time, start_date, entered_on)
            
            if worker_name not in prepared_data:
                prepared_data[worker_name] = {}
            prepared_data[worker_name][date] = status
            
    return prepared_data

def get_absence_status(total_units, unit_of_time, start_date, entered_on):
    if unit_of_time == 'Days':
        if entered_on > start_date:
            return 'Unplanned Absence'
        else:
            return 'Planned Absence'
    
    total_hours = int(total_units)
    if total_hours <= 2:
        return '75% Available'
    elif total_hours <= 5:
        return '50% Available'
    elif total_hours < 8:
        return '25% Available'
    else:
        return 'Planned Absence'

# PagerDuty Functions
# PagerDuty Functions
def get_pagerduty_schedule_for_timeframe(start_date, end_date):
    schedule_url = f'https://api.pagerduty.com/schedules/{Config.PD_SCHEDULE_ID}'
    headers = {
        'Accept': 'application/vnd.pagerduty+json;version=2',
        'Authorization': f'Token token={Config.PD_API_KEY}'
    }
    
    params = {
        'since': start_date.isoformat(),
        'until': end_date.isoformat(),
        'overflow': 'true'
    }
    
    # If time_zone parameter is causing issues, remove it from params
    
    response = requests.get(schedule_url, headers=headers, params=params)
    schedule_details = response.json()
    
    # Print the entire response structure to debug
    print(f"API Response Keys: {schedule_details.keys()}")
    if 'schedule' in schedule_details:
        print(f"Schedule Keys: {schedule_details['schedule'].keys()}")
    
    # Instead of accessing schedule_layers, we need to access final_schedule
    if 'schedule' in schedule_details and 'final_schedule' in schedule_details['schedule']:
        return schedule_details['schedule']['final_schedule']['rendered_schedule_entries']
    
    # If the above path doesn't exist, fall back to schedule_layers for backward compatibility
    return schedule_details.get('schedule', {}).get('schedule_layers', [])

def update_with_pagerduty_data(final_schedule_entries):
    support_data = {}
    
    # Check if we're dealing with the old format (layers) or new format (entries)
    if final_schedule_entries and isinstance(final_schedule_entries, list) and 'rendered_schedule_entries' in final_schedule_entries[0]:
        # Old format - process schedule layers
        for layer in final_schedule_entries:
            for entry in layer.get('rendered_schedule_entries', []):
                process_entry(entry, support_data)
    else:
        # New format - direct entries from final_schedule
        for entry in final_schedule_entries:
            process_entry(entry, support_data)
    
    return support_data

def process_entry(entry, support_data):
    user = entry['user']['summary']
    
    # Convert start and end times to datetime objects
    # Handle timezone information if present
    start_time_str = entry['start']
    end_time_str = entry['end']
    
    # Remove timezone part if it causes issues
    if start_time_str.endswith('Z'):
        start_time_str = start_time_str[:-1]
    if end_time_str.endswith('Z'):
        end_time_str = end_time_str[:-1]
        
    # Try different formats based on what's returned
    try:
        # Try ISO format first
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
    except ValueError:
        try:
            # Try without the timezone part
            if '+' in start_time_str:
                start_time_str = start_time_str.split('+')[0]
            if '+' in end_time_str:
                end_time_str = end_time_str.split('+')[0]
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            # Last resort: use a more forgiving parser
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S")
            end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M:%S")
    
    if user not in support_data:
        support_data[user] = []
    
    # Define support hours reference times
    morning_cutoff = datetime(1900, 1, 1, 12, 0).time()  # 12:00 PM
    evening_cutoff = datetime(1900, 1, 1, 17, 0).time()  # 5:00 PM
    
    if start_time.date() == end_time.date():
        # Single day support shift
        if (start_time.time() <= morning_cutoff and 
            end_time.time() >= evening_cutoff and 
            start_time.weekday() not in [5, 6]):
            support_data[user].append(start_time.strftime("%Y-%m-%d"))
    else:
        # Multi-day support shift
        # Check first day
        if (start_time.time() < morning_cutoff and 
            start_time.weekday() not in [5, 6]):
            support_data[user].append(start_time.strftime("%Y-%m-%d"))
        
        # Add all full days in between
        next_day = start_time + timedelta(days=1)
        while next_day.date() < end_time.date():
            if next_day.weekday() not in [5, 6]:  # Excluding weekends
                support_data[user].append(next_day.strftime("%Y-%m-%d"))
            next_day += timedelta(days=1)
        
        # Check last day
        if (end_time.time() >= evening_cutoff and 
            end_time.weekday() not in [5, 6]):
            support_data[user].append(end_time.strftime("%Y-%m-%d"))

# Holiday Functions
def fetch_public_holidays(country_code, year):
    url = f"https://date.nager.at/api/v3/publicholidays/{year}/{country_code}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def is_holiday_applicable(holiday, member_county):
    if holiday['global']:
        return True
    if 'counties' in holiday and holiday['counties'] is not None:
        return member_county in holiday['counties']
    return False

def get_holidays_for_period(start_date, end_date, country_code):
    holidays = fetch_public_holidays(country_code, start_date.year)
    if start_date.year != end_date.year:
        holidays += fetch_public_holidays(country_code, end_date.year)
    return list({h['date']: h for h in holidays}.values())

def fetch_holidays(team_data, start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    holidays = {}
    
    for member, data in team_data.items():
        location = data['location']
        country_code = location.split('-')[0]
        member_county = location if '-' in location else None
        public_holidays = get_holidays_for_period(start_date, end_date, country_code)
        
        member_holidays = [h['date'] for h in public_holidays 
                         if is_holiday_applicable(h, member_county)]
        holidays[member] = {
            date: 'Public Holiday' 
            for date in member_holidays 
            if start_date <= datetime.strptime(date, '%Y-%m-%d').date() <= end_date
        }
    
    return holidays

# Part-time Schedule Functions
def get_dates_for_day_of_week(start_date, end_date, day_of_week):
    day_mapping = {
        "mon": 0, "tue": 1, "wed": 2, "thu": 3, 
        "fri": 4, "sat": 5, "sun": 6
    }
    weekday_num = day_mapping[day_of_week.lower()]
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == weekday_num:
            dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    return dates

def add_non_workdays_to_team_data(team_data, start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    part_time = {}
    
    for name, data in team_data.items():
        nonwork_days = data.get('nonwork', [])
        part_time[name] = {}
        for day in nonwork_days:
            non_work_dates = get_dates_for_day_of_week(start_date, end_date, day)
            for date in non_work_dates:
                part_time[name][date] = 'No Workday'
    
    return part_time

# Calendar Generation Functions
def generate_sprint_dates(start_date, end_date):
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    
    sprint_dates = []
    current_date = start_date_obj
    while current_date <= end_date_obj:
        if current_date.weekday() < 5:  # Exclude weekends
            sprint_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    return sprint_dates

# Routes
@app.route('/')
def index():
    return render_template('index.html', team_data=team_data)

@app.route('/generate_calendar', methods=['POST'])
def generate_calendar():
    data = request.get_json()
    start_date = data['start_date']
    end_date = data['end_date']
    
    sprint_dates = generate_sprint_dates(start_date, end_date)
    
    pd_schedule = get_pagerduty_schedule_for_timeframe(
        datetime.strptime(start_date, "%Y-%m-%d"),
        datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    )
    pagerduty_data = update_with_pagerduty_data(pd_schedule)
    
    raw_absence_data = fetch_absence_data(start_date, end_date)
    prepared_absence_data = prepare_workday_absence_data(
        raw_absence_data, team_data, start_date
    ) if raw_absence_data else None
    
    holiday_data = fetch_holidays(team_data, start_date, end_date)
    part_time = add_non_workdays_to_team_data(team_data, start_date, end_date)
    
    return jsonify({
        'sprint_dates': sprint_dates,
        'pagerduty_data': pagerduty_data,
        'absence_data': prepared_absence_data,
        'holiday_data': holiday_data,
        'part_time': part_time,
        'team_data': team_data
    })

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    name = data['name']
    date = data['date']
    status = data['status']
    
    if name in team_data:
        team_data[name]['statuses'][date] = status
        return jsonify({'success': True})
    return jsonify({'success': False})



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)