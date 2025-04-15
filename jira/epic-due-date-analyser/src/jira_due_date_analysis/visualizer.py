"""Visualization logic for the Jira Due Date Analysis tool."""

import textwrap
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional
import csv
import os
from datetime import datetime, timedelta, timezone
from .models import AnalysisResult
from .utils import format_duration
import logging
import pandas as pd
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from jira_due_date_analysis.weekly_extension import get_next_friday



logger = logging.getLogger(__name__)

class DueDateVisualizer:
    """Creates visualizations for due date shift analysis."""
    
    def __init__(self, result: AnalysisResult):
        """Initialize the visualizer with analysis results."""
        self.result = result


    def export_to_csv(self, output_dir: str, prefix: Optional[str] = None):
        """Export the date shifts to a CSV file for debugging."""
        deliverable_shifts = self.result.date_shifts

        # Sort deliverables by key
        deliverable_shifts.sort(key=lambda x: x.issue_key)

        # Find the maximum number of shifts
        max_shifts = max((len(shift.date_changes) for shift in deliverable_shifts), default=0)

        # Create row labels
        row_labels = ['Start Date']
        for i in range(max_shifts):
            row_labels.extend([
                f'Change Date {i+1}',
                f'Due Date {i+1}'
            ])
        
        # Initialize data dictionary with empty strings
        data = {
            'Row Type': row_labels
        }
        
        # Fill in data for each deliverable
        for shift in deliverable_shifts:
            column_data = []
            # Add start date
            column_data.append(shift.start_date.strftime('%Y-%m-%d %H:%M:%S %z'))
            
            # Add change and due dates
            for i in range(max_shifts):
                if i < len(shift.date_changes):
                    change_date, shift_date = shift.date_changes[i]
                    column_data.append(change_date.strftime('%Y-%m-%d %H:%M:%S %z'))
                    column_data.append(shift_date.strftime('%Y-%m-%d %H:%M:%S %z'))
                else:
                    column_data.extend(['', ''])  # Empty strings for missing data
            
            data[shift.issue_key] = column_data

        # Create DataFrame
        df = pd.DataFrame(data)
        
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        csv_path = os.path.join(output_dir, f"{prefix}_date_shifts.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Date shifts exported to {csv_path}")
        
        # Print the data for immediate debugging
        print("\nDate Shifts Analysis:")
        print(df.to_string())
        
    def create_shift_chart(self, 
                      figsize: tuple = (12, 6),
                      color_map: str = 'Blues',
                      min_color: float = 0.3,
                      max_color: float = 0.9) -> plt.Figure:
        """Create a stacked bar chart showing due date shifts."""
        fig, ax = plt.subplots(figsize=figsize)
        
        deliverable_shifts = self.result.date_shifts
        # Sort shifts by total delay for better visualization
        # sorted_shifts = sorted(
        #     deliverable_shifts,
        #     key=lambda x: x.total_delay,
        #     reverse=True
        # )
        sorted_shifts = deliverable_shifts
        logger.info(f"Creating visualization for {len(sorted_shifts)} deliverables")
        
        # Define markers and colors for different date types
        date_styles = {
            'deliverable_start': {'color': 'black', 'marker': 'o', 'label': 'Deliverable Start'},
            'deliverable_progress': {'color': 'black', 'marker': '^', 'label': 'Deliverable In Progress'},
            'epic_start': {'color': '#9747FF', 'marker': 'o', 'label': 'Epic Start'},
            'epic_progress': {'color': '#9747FF', 'marker': '^', 'label': 'Epic In Progress'},
            'issue_progress': {'color': '#4D97FF', 'marker': '^', 'label': 'Issue In Progress'},
            'end_date': {'color': '#57B894', 'marker': 's', 'label': 'Done Date'}
        }
        legend_added = set()  # Track which styles we've already added to the legend
        
        for idx, shift in enumerate(sorted_shifts):
            if not shift.shifts:
                continue
            
            # Calculate bar segments
            days_from_start = []
            for due_date in sorted(shift.shifts):
                days = (due_date - shift.start_date).days
                days_from_start.append(days)
            
            days_from_start.sort()
            
            # Plot bar segments
            colors = plt.cm.get_cmap(color_map)(np.linspace(min_color, max_color, len(days_from_start)))
            wrapped_label = "\n".join(textwrap.wrap(shift.issue_key + '-' + shift.issue_summary, width=25))
            
            bottom = 0
            for i, days in enumerate(days_from_start):
                height = days - bottom
                plt.bar(wrapped_label, height, bottom=bottom,
                    color=colors[i],
                    label=f'Due Date {i+1}' if idx == 0 else "")
                bottom = days

            # Add total delay annotation on top of the bar
            if shift.total_delay is not None:
                y_pos = max(days_from_start)  # Position at the top of the bar
                plt.text(idx, y_pos, f'delay: {shift.total_delay}d',
                        ha='center', va='bottom',
                        fontsize=8,
                        rotation=0)

            # Plot start dates and transitions **** skip if start_dates.skip is true
            deliverable_dates = next((dates for dates in self.result.start_dates 
                                    if dates.deliverable_key == shift.issue_key), None)
            
            if deliverable_dates:
                # Helper function to plot date indicator
                def plot_date(date_value, style_key):
                    if date_value:
                        days = (date_value - shift.start_date).days
                        style = date_styles[style_key]
                        label = style['label'] if style_key not in legend_added else ""
                        plt.scatter(idx, days, color=style['color'], marker=style['marker'], 
                                s=50, zorder=5, label=label)
                        if label:
                            legend_added.add(style_key)
                
                # Plot all date indicators
                if self.result.show_start_dates and self.result.start_dates[0].skip_deliverable == False:
                    plot_date(deliverable_dates.deliverable_start, 'deliverable_start')
                    plot_date(deliverable_dates.deliverable_in_progress, 'deliverable_progress')
                    plot_date(deliverable_dates.earliest_epic_start, 'epic_start')
                    plot_date(deliverable_dates.earliest_epic_in_progress, 'epic_progress')
                    plot_date(deliverable_dates.earliest_issue_in_progress, 'issue_progress')
                
                # Plot end date
                if shift.end_date:
                    done_days = (shift.end_date - shift.start_date).days
                    style = date_styles['end_date']
                    label = style['label'] if 'end_date' not in legend_added else ""
                    plt.scatter(idx, done_days, color=style['color'], marker=style['marker'], 
                            s=100, zorder=5, label=label)
                    if label:
                        legend_added.add('end_date')
        
        # Customize the chart
        plt.title(f'Due Date Shifts Analysis for {self.result.team}\n'
                f'Scenario: {self.result.scenario.value}')
        plt.xlabel('Deliverable Key')
        plt.ylabel('Days from Start Date')
        plt.xticks(rotation=45, ha='right')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add summary statistics
        summary = (
            f'Deliverables analyzed: {len(deliverable_shifts)}\n'
            f'Average shifts: {self.result.average_shifts:.1f}\n'
            # f'Average delay: {format_duration(int(self.result.average_delay))}'
        )
        plt.figtext(0.02, 0.02, summary, fontsize=8)
        
        plt.tight_layout()
        return fig

    def create_summary_chart(self, figsize: tuple = (8, 6)) -> plt.Figure:
        """Create a summary chart showing distribution of shifts."""
        fig, ax = plt.subplots(figsize=figsize)
        
        # Filter for Deliverables only
        deliverable_shifts = [
            shift for shift in self.result.date_shifts 
            if shift.issue_type == 'Deliverable'
        ]
        
        # Calculate shift distribution
        shift_counts = [shift.total_shifts for shift in deliverable_shifts]
        
        if not shift_counts:
            logger.warning("No shifts found for visualization")
            return fig
            
        # Create histogram
        plt.hist(shift_counts, bins=range(max(shift_counts) + 2),
                rwidth=0.8, align='left')
        
        plt.title(f'Distribution of Due Date Shifts\n{self.result.team}')
        plt.xlabel('Number of Shifts')
        plt.ylabel('Number of Deliverables')
        plt.grid(True, alpha=0.3)
        
        # Add mean line
        mean_shifts = sum(shift_counts) / len(shift_counts)
        plt.axvline(mean_shifts, color='red', linestyle='dashed', linewidth=1)
        plt.text(mean_shifts + 0.1, plt.ylim()[1] * 0.9,
                f'Mean: {mean_shifts:.1f}',
                rotation=90)
        
        plt.tight_layout()
        return fig
    
    def create_weekly_timeline_chart(self, 
                                figsize: tuple = (14, 8),
                                marker_size: int = 6,
                                line_width: float = 1.2,
                                grid_alpha: float = 0.3) -> plt.Figure:
        """
        Create a timeline chart showing due dates for each Friday.
        
        X-axis: Fridays (weekly snapshots)
        Y-axis: What the due date was on each Friday
        
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Collect all deliverables with weekly snapshots
        deliverables = self.result.date_shifts
        
        # Add detailed logging about what we're processing
        for d in deliverables:
            logger.info(f"Deliverable {d.issue_key} has {len(d.date_changes)} date changes and {len(d.weekly_snapshots)} weekly snapshots")
            if d.weekly_snapshots:
                first_snapshot = d.weekly_snapshots[0]
                last_snapshot = d.weekly_snapshots[-1]
                logger.info(f"  - First snapshot: {first_snapshot[0].strftime('%Y-%m-%d')} -> {first_snapshot[1].strftime('%Y-%m-%d')}")
                logger.info(f"  - Last snapshot: {last_snapshot[0].strftime('%Y-%m-%d')} -> {last_snapshot[1].strftime('%Y-%m-%d')}")
        
        deliverables_with_snapshots = [d for d in deliverables if d.weekly_snapshots]
        
        if not deliverables_with_snapshots:
            logger.warning(f"No deliverables with weekly snapshots found out of {len(deliverables)} total deliverables")
            plt.title("No data available for weekly timeline visualization")
            return fig
            
        logger.info(f"Creating weekly visualization for {len(deliverables_with_snapshots)} deliverables with snapshots")
        
        # Create a colormap for different deliverables
        import matplotlib.colors as mcolors
        colors = plt.cm.tab20(np.linspace(0, 1, len(deliverables_with_snapshots)))
        
        # Create a legend mapping
        legend_elements = []
        
        # Track all dates for axis limits
        all_friday_dates = []
        all_due_dates = []
        
        # Plot each deliverable's timeline
        for idx, shift in enumerate(deliverables_with_snapshots):
            deliverable_color = colors[idx]
            
            # Get the Friday dates and current due dates
            friday_dates = [friday for friday, _ in shift.weekly_snapshots]
            due_dates = [due_date for _, due_date in shift.weekly_snapshots]
            
            # Add to the collections for axis limits
            all_friday_dates.extend(friday_dates)
            all_due_dates.extend(due_dates)
            
            # Plot the weekly timeline for this deliverable
            ax.plot(friday_dates, due_dates, 
                    'o-', 
                    color=deliverable_color, 
                    markersize=marker_size, 
                    linewidth=line_width,
                    label=shift.issue_key)
            
            # Add the end date (resolution date) if available
            if shift.end_date and friday_dates:
                # Find the closest Friday to the resolution date
                closest_friday_idx = min(range(len(friday_dates)), 
                                    key=lambda i: abs((friday_dates[i] - shift.end_date).total_seconds()))
                
                closest_friday = friday_dates[closest_friday_idx]
                due_date_at_resolution = due_dates[closest_friday_idx]
                
                # Plot the end date with a diamond marker
                ax.plot([closest_friday], [due_date_at_resolution], 
                        marker='D', 
                        markersize=8, 
                        color=deliverable_color,
                        markeredgecolor=deliverable_color,
                        markeredgewidth=1.5)
            
            # Add a legend entry
            legend_elements.append(plt.Line2D([0], [0], 
                                        marker='o', 
                                        color='w', 
                                        markerfacecolor=deliverable_color, 
                                        markersize=6, 
                                        label=f"{shift.issue_key} - {shift.issue_summary}"))
        
        # Add a legend entry for the end date marker
        legend_elements.append(plt.Line2D([0], [0], 
                                    marker='D', 
                                    color='w', 
                                    markerfacecolor='gray', 
                                    markeredgecolor='black',
                                    markeredgewidth=1.5,
                                    markersize=8, 
                                    label='Resolution Date'))
        
        # Set axis labels and title
        ax.set_xlabel('Fridays (Weekly Snapshots)')
        ax.set_ylabel('Due Date')
        ax.set_title(f'Weekly Due Date Timeline for {self.result.team}\nWhat the due date was on each Friday')
        
        # Format dates on the axes
        import matplotlib.dates as mdates
        
        # Set up the x-axis to show dates properly
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))  # Month and Year
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=4))  # Friday
        
        # Format y-axis with dates
        ax.yaxis.set_major_formatter(mdates.DateFormatter('%b %d, %Y'))
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Get today's date for marking on the chart
        today = datetime.now(timezone.utc)
        
        # Ensure all data points are visible by setting proper limits
        if all_friday_dates and all_due_dates:
            buffer = timedelta(days=7)  # One week buffer
            
            # Make sure today's date is included in the x-axis range
            x_min = min(min(all_friday_dates), today - buffer)
            x_max = max(max(all_friday_dates), today + buffer)
            y_min = min(all_due_dates) - buffer
            y_max = max(all_due_dates) + buffer
            
            # Set limits with some padding
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            
            # Log the date ranges to help with debugging
            logger.info(f"X-axis range: {x_min.strftime('%Y-%m-%d')} to {x_max.strftime('%Y-%m-%d')}")
            logger.info(f"Y-axis range: {y_min.strftime('%Y-%m-%d')} to {y_max.strftime('%Y-%m-%d')}")
        
        # Add a grid for easier reading
        ax.grid(True, which='minor', alpha=grid_alpha/2, linestyle=':')
        ax.grid(True, which='major', alpha=grid_alpha, linestyle='-')
        
        # Add a HORIZONTAL line for today's date on the y-axis
        ax.axhline(y=today, color='lightgray', linestyle='--', linewidth=2, alpha=0.7)
        
        # Add text label for today's date
        # Position it near the right edge of the x-axis
        x_pos = ax.get_xlim()[1] - (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.02  # Position near right edge
        ax.text(x_pos, today, f"Today ({today.strftime('%Y-%m-%d')})", 
                color='lightgray',  rotation=0, va='bottom', ha='left')
        
        # Add today's date to the legend
        legend_elements.append(plt.Line2D([0], [0], 
                                    color='lightgray', 
                                    linestyle='--',
                                    linewidth=1,
                                    label="Today's Date"))
        
        # Add the legend outside the plot
        ax.legend(handles=legend_elements, 
                loc='center left', 
                bbox_to_anchor=(1, 0.5),
                fontsize=8)
        
        # Add a note explaining the chart
        ax.text(0.05, 0.95, 
                "Each point represents the due date\nas it was on a given Friday.\nFlat lines indicate periods with\nno due date changes.",
                transform=ax.transAxes,
                fontsize=8,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        plt.tight_layout()
        return fig

    def export_weekly_timeline_data(self, output_dir: str, prefix: Optional[str] = None):
        """Export the weekly timeline data to a CSV file."""
        # Filter for deliverables with weekly snapshots
        deliverables = self.result.date_shifts
        
        # Log details about all deliverables
        logger.info(f"Checking {len(deliverables)} deliverables for weekly snapshots")
        for d in deliverables:
            logger.info(f"Deliverable {d.issue_key} has {len(d.date_changes)} date changes and {len(d.weekly_snapshots)} weekly snapshots")
            if d.weekly_snapshots and len(d.weekly_snapshots) > 0:
                first_date = d.weekly_snapshots[0][0]
                last_date = d.weekly_snapshots[-1][0]
                logger.info(f"  - Weekly snapshots for {d.issue_key} span from {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}")
        
        deliverables_with_snapshots = [d for d in deliverables if d.weekly_snapshots]
        
        if not deliverables_with_snapshots:
            logger.warning("No deliverables with weekly snapshots found for export")
            return
        
        logger.info(f"Exporting weekly data for {len(deliverables_with_snapshots)} deliverables")
        
        # Create data for CSV
        rows = []
        for shift in deliverables_with_snapshots:
            for i, (friday_date, due_date) in enumerate(shift.weekly_snapshots):
                # Check if this snapshot is at or near the resolution date
                is_resolution_week = False
                days_after_friday = 0
                
                if shift.end_date:
                    # If the end date is within 7 days after this Friday
                    days_after_friday = (shift.end_date - friday_date).days
                    is_resolution_week = 0 <= days_after_friday < 7
                
                rows.append({
                    'DeliverableKey': shift.issue_key,
                    'DeliverableSummary': shift.issue_summary,
                    'WeekIndex': i + 1,
                    'FridayDate': friday_date.strftime('%Y-%m-%d'),
                    'DueDate': due_date.strftime('%Y-%m-%d'),
                    'DaysUntilDue': (due_date - friday_date).days,
                    'IsResolutionWeek': is_resolution_week,
                    'DaysToResolution': days_after_friday if shift.end_date else None,
                    'StartDate': shift.start_date.strftime('%Y-%m-%d'),
                    'EndDate': shift.end_date.strftime('%Y-%m-%d') if shift.end_date else ''
                })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to CSV
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        csv_path = os.path.join(output_dir, f"{prefix}_weekly_timeline.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Weekly timeline data exported to {csv_path} ({len(rows)} rows)")
        
        # Print a preview
        print("\nWeekly Timeline Data Preview:")
        preview = df.head(10)  # Show more rows to diagnose issues
        print(preview.to_string())
        
        # Show summary by deliverable
        deliverable_summary = df.groupby('DeliverableKey').agg({
            'WeekIndex': 'count', 
            'FridayDate': ['min', 'max']
        })
        deliverable_summary.columns = ['WeekCount', 'FirstFriday', 'LastFriday']
        print("\nWeekly Timeline Summary by Deliverable:")
        print(deliverable_summary.to_string())


    def save_charts(self, output_dir: str, prefix: Optional[str] = None):
        """Save all charts and data to the specified directory."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        
        # Export the date shifts to CSV
        self.export_to_csv(output_dir, prefix)

        # Export weekly timeline data to CSV
        self.export_weekly_timeline_data(output_dir, prefix)
        
        # Temporarily store original show_start_dates value
        original_show_start_dates = self.result.show_start_dates
        
        # Save shift chart without start dates
        self.result.show_start_dates = False
        shift_chart = self.create_shift_chart()
        shift_chart.savefig(
            os.path.join(output_dir, f"{prefix}_shifts_basic.png"),
            bbox_inches='tight',
            dpi=300
        )
        
        # Save shift chart with start dates
        self.result.show_start_dates = True
        shift_chart_with_dates = self.create_shift_chart()
        shift_chart_with_dates.savefig(
            os.path.join(output_dir, f"{prefix}_shifts_with_dates.png"),
            bbox_inches='tight',
            dpi=300
        )
        
        # Save weekly timeline chart
        weekly_timeline_chart = self.create_weekly_timeline_chart()
        weekly_timeline_chart.savefig(
            os.path.join(output_dir, f"{prefix}_weekly_timeline.png"),
            bbox_inches='tight',
            dpi=300
        )
        
        # Restore original value
        self.result.show_start_dates = original_show_start_dates
        
        # Save summary chart
        summary_chart = self.create_summary_chart()
        summary_chart.savefig(
            os.path.join(output_dir, f"{prefix}_summary.png"),
            bbox_inches='tight',
            dpi=300
        )
        
        plt.close('all')