// Global variables
let team_data;
let sprintDates = [];

const statusToPlannedCapacity = {
    "Available": 1,
    "Planned Absence": 0,
    "Public Holiday": 0,
    "No Workday": 0,
    "Unplanned Absence": 1,
    "On Support": 0,
    "50% Available": 0.5,
    "25% Available": 0.25,
    "75% Available": 0.75,
    "Other Project": 0,
    "Onboarding": 1
};

const statusColors = {
    "Available": "#d1dd93",
    "On Support": "#c2d5f4",
    "Planned Absence": "#FFB092",
    "Public Holiday": "#C3B1E1",
    "No Workday": "#CCCCCC",
    "75% Available": "#f0edaa",
    "50% Available": "#f0edaa",
    "25% Available": "#f0edaa",
    "Unplanned Absence": "#ff8c8c",
    "Other Project": "#bdeeed",
    "Onboarding": "#bdeeed"
};

function generateSprintCalendar() {
    const startDate = document.getElementById("start_date").value;
    const endDate = document.getElementById("end_date").value;
    
    if (!startDate || !endDate) {
        alert("Please select both start and end dates");
        return;
    }
    
    fetch('/generate_calendar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            start_date: startDate,
            end_date: endDate
        })
    })
    .then(response => response.json())
    .then(data => {
        team_data = data.team_data;
        sprintDates = data.sprint_dates;
        createCalendarTable(data);
        updateAllStatuses(data);
        updateAllCellColors();
        updateTotalCapacity();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to generate calendar. Please check console for details.');
    });
}

function createCalendarTable(data) {
    let tableHtml = '<table><tr><th>Team Member</th>';
    
    // Add date headers
    for (const date of data.sprint_dates) {
        tableHtml += `<th>${date}</th>`;
    }
    tableHtml += '</tr>';
    
    // Add rows for each team member
    for (const [name, details] of Object.entries(data.team_data)) {
        tableHtml += `<tr><td>${name}</td>`;
        
        for (const date of data.sprint_dates) {
            tableHtml += `<td>
                <select id="status_${name}_${date}" onchange="updateStatus('${name}', '${date}')">
                    ${generateStatusOptions()}
                </select>
            </td>`;
        }
        tableHtml += '</tr>';
    }
    
    // Add total capacity row
    tableHtml += `<tr>
        <td colspan="2">Total Capacity</td>
        <td id="total_capacity" colspan="${data.sprint_dates.length - 1}"></td>
    </tr>`;
    
    tableHtml += '</table>';
    
    document.getElementById("sprint_calendar").innerHTML = tableHtml;
}

function generateStatusOptions() {
    const statuses = [
        "Available", "Planned Absence", "Public Holiday", "No Workday",
        "Unplanned Absence", "On Support", "50% Available", "25% Available",
        "75% Available", "Other Project", "Onboarding"
    ];
    
    return statuses.map(status => 
        `<option value="${status}">${status}</option>`
    ).join('');
}

function updateStatus(name, date) {
    const statusElement = document.getElementById(`status_${name}_${date}`);
    const status = statusElement.value;
    
    fetch('/update_status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: name,
            date: date,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            team_data[name].statuses[date] = status;
            updateStatusColor(name, date);
            updateTotalCapacity();
        }
    })
    .catch(error => console.error('Error:', error));
}

function updateStatusColor(name, date) {
    const statusElement = document.getElementById(`status_${name}_${date}`);
    const selectedStatus = statusElement.value;
    const color = statusColors[selectedStatus] || "#FFFFFF";
    statusElement.style.backgroundColor = color;
}

function updateAllStatuses(data) {
    // Update from PagerDuty data
    if (data.pagerduty_data) {
        for (const [name, dates] of Object.entries(data.pagerduty_data)) {
            for (const date of dates) {
                const element = document.getElementById(`status_${name}_${date}`);
                if (element) {
                    element.value = "On Support";
                    team_data[name].statuses[date] = "On Support";
                }
            }
        }
    }
    
    // Update from absence data
    if (data.absence_data) {
        for (const [name, dates] of Object.entries(data.absence_data)) {
            for (const [date, status] of Object.entries(dates)) {
                const element = document.getElementById(`status_${name}_${date}`);
                if (element) {
                    element.value = status;
                    team_data[name].statuses[date] = status;
                }
            }
        }
    }
    
    // Update from holiday data
    if (data.holiday_data) {
        for (const [name, dates] of Object.entries(data.holiday_data)) {
            for (const [date, status] of Object.entries(dates)) {
                const element = document.getElementById(`status_${name}_${date}`);
                if (element) {
                    element.value = status;
                    team_data[name].statuses[date] = status;
                }
            }
        }
    }
    
    // Update from part-time data
    if (data.part_time) {
        for (const [name, dates] of Object.entries(data.part_time)) {
            for (const [date, status] of Object.entries(dates)) {
                const element = document.getElementById(`status_${name}_${date}`);
                if (element) {
                    element.value = status;
                    team_data[name].statuses[date] = status;
                }
            }
        }
    }
}

function updateAllCellColors() {
    const selects = document.getElementsByTagName("select");
    for (const select of selects) {
        const [_, name, date] = select.id.split("_");
        updateStatusColor(name, date);
    }
}

function updateTotalCapacity() {
    let maxCapacity = 0;
    let totalPlannedCapacity = 0;
    let totalActualCapacity = 0;
    
    for (const [name, details] of Object.entries(team_data)) {
        maxCapacity += details.capacity;
        
        for (const date of sprintDates) {
            const statusElement = document.getElementById(`status_${name}_${date}`);
            if (!statusElement) continue;
            
            const status = statusElement.value;
            if (status === "Available") {
                totalActualCapacity += 1;
                totalPlannedCapacity += 1;
            } else if (status === "Unplanned Absence") {
                totalPlannedCapacity += 1;
            }
        }
    }
    
    document.getElementById("total_capacity").innerHTML =
        `Max: ${maxCapacity} days, ` +
        `Planned: ${totalPlannedCapacity.toFixed(1)} days, ` +
        `Actual: ${totalActualCapacity.toFixed(1)} days`;
}

