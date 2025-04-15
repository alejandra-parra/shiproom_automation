"""Visualization logic for the Jira Due Date Analysis tool."""

import textwrap
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional
import csv
import os
from datetime import datetime
from .models import AnalysisResult
from .utils import format_duration
import logging
import pandas as pd

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
    
    def create_timeline_chart(self, 
                            figsize: tuple = (14, 8),
                            marker_size: int = 80,
                            line_width: float = 1.5,
                            date_format: str = '%Y-%m-%d') -> plt.Figure:
        """
        Create a timeline matrix chart showing when due dates were changed and what they were changed to.
        
        X-axis: When the change was made (change date)
        Y-axis: What the due date was changed to (shift date)
        
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Collect all deliverables with their date changes
        deliverables = self.result.date_shifts
        deliverables_with_changes = [d for d in deliverables if d.date_changes]
        
        if not deliverables_with_changes:
            logger.warning("No deliverables with date changes found for timeline visualization")
            plt.title("No data available for timeline visualization")
            return fig
        
        # Create a colormap for different deliverables
        import matplotlib.colors as mcolors
        colors = plt.cm.tab20(np.linspace(0, 1, len(deliverables_with_changes)))
        
        # Create a legend mapping
        legend_elements = []
        
        # Track all dates for axis limits
        all_change_dates = []
        all_shift_dates = []
        
        # Plot each deliverable's timeline
        for idx, shift in enumerate(deliverables_with_changes):
            deliverable_color = colors[idx]
            
            # Get the change and shift dates
            change_dates = [change_date for change_date, _ in shift.date_changes]
            shift_dates = [shift_date for _, shift_date in shift.date_changes]
            
            # Add to the collections for axis limits
            all_change_dates.extend(change_dates)
            all_shift_dates.extend(shift_dates)
            
            # Plot the timeline for this deliverable
            # The change dates are on the x-axis, the shift dates on the y-axis
            ax.plot(change_dates, shift_dates, 
                    'o-', 
                    color=deliverable_color, 
                    markersize=8, 
                    linewidth=line_width,
                    label=shift.issue_key)
            
            # Highlight the start point with a different marker and size
            if shift.date_changes:
                first_change_date, first_shift_date = shift.date_changes[0]
                ax.plot([first_change_date], [first_shift_date], 
                        marker='s', 
                        markersize=10, 
                        color=deliverable_color,
                        markeredgecolor='black',
                        markeredgewidth=1.5)
            
            # Add labels for the points
            for i, (change_date, shift_date) in enumerate(shift.date_changes):
                # Add a small text annotation for the point index
                ax.annotate(f"{i+1}", 
                        (change_date, shift_date),
                        xytext=(5, 5),
                        textcoords="offset points",
                        fontsize=8)
            
            # Add a legend entry
            legend_elements.append(plt.Line2D([0], [0], 
                                        marker='o', 
                                        color='w', 
                                        markerfacecolor=deliverable_color, 
                                        markersize=6, 
                                        label=f"{shift.issue_key} - {shift.issue_summary}"))
        
        # Set axis labels and title
        ax.set_xlabel('Date when due date was changed')
        ax.set_ylabel('Date that was set as due date')
        ax.set_title(f'Due Date Changes Timeline for {self.result.team}\nWhen changes were made vs. What they were changed to')
        
        # Format dates on the axes
        import matplotlib.dates as mdates
        date_formatter = mdates.DateFormatter(date_format)
        ax.xaxis.set_major_formatter(date_formatter)
        ax.yaxis.set_major_formatter(date_formatter)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add diagonal line where x=y (change date = shift date)
        # This line separates realistic changes (points below the line)
        # from impossible ones (points above the line)
        if all_change_dates and all_shift_dates:
            min_date = min(min(all_change_dates), min(all_shift_dates))
            max_date = max(max(all_change_dates), max(all_shift_dates))
            ax.plot([min_date, max_date], [min_date, max_date], 
                    'k--', alpha=0.5, linewidth=1,
                    label='Change date = Shift date')
            
            # Add a note explaining the diagonal line
            ax.text(0.05, 0.95, 
                    "Points below the diagonal line represent\ndue dates set in the future",
                    transform=ax.transAxes,
                    fontsize=8,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
            
            # Add a note explaining the square markers
            ax.text(0.05, 0.85, 
                    "Square markers indicate\ninitial due date setting",
                    transform=ax.transAxes,
                    fontsize=8,
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        # Add a grid for easier reading
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Add the legend outside the plot
        ax.legend(handles=legend_elements, 
                loc='center left', 
                bbox_to_anchor=(1, 0.5),
                fontsize=8)
        
        plt.tight_layout()
        return fig

    def export_timeline_data(self, output_dir: str, prefix: Optional[str] = None):
        """Export the timeline data to a CSV file."""
        # Filter for deliverables with date changes
        deliverables = self.result.date_shifts
        deliverables_with_changes = [d for d in deliverables if d.date_changes]
        
        if not deliverables_with_changes:
            logger.warning("No deliverables with date changes found for timeline export")
            return
        
        # Create data for CSV
        rows = []
        for shift in deliverables_with_changes:
            for i, (change_date, shift_date) in enumerate(shift.date_changes):
                is_initial = i == 0  # Mark the first change as the initial setting
                
                rows.append({
                    'DeliverableKey': shift.issue_key,
                    'DeliverableSummary': shift.issue_summary,
                    'ChangeIndex': i + 1,
                    'IsInitialSetting': is_initial,
                    'ChangeDate': change_date.strftime('%Y-%m-%d %H:%M:%S %z'),
                    'ShiftDate': shift_date.strftime('%Y-%m-%d %H:%M:%S %z'),
                    'DaysSetInFuture': (shift_date - change_date).days,
                    'StartDate': shift.start_date.strftime('%Y-%m-%d %H:%M:%S %z'),
                    'EndDate': shift.end_date.strftime('%Y-%m-%d %H:%M:%S %z') if shift.end_date else ''
                })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Save to CSV
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        csv_path = os.path.join(output_dir, f"{prefix}_timeline_data.csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Timeline data exported to {csv_path}")
        
        # Print a preview
        print("\nTimeline Data Preview:")
        print(df.head().to_string())

    def save_charts(self, output_dir: str, prefix: Optional[str] = None):
        """Save all charts and data to the specified directory."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        
        # Export the date shifts to CSV
        self.export_to_csv(output_dir, prefix)
        
        # Export timeline data to CSV
        self.export_timeline_data(output_dir, prefix)
        
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
        
        # Save timeline chart
        timeline_chart = self.create_timeline_chart()
        timeline_chart.savefig(
            os.path.join(output_dir, f"{prefix}_timeline.png"),
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