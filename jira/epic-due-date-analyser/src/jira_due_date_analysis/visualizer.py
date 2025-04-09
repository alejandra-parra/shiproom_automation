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
        # deliverable_shifts = [
        #     shift for shift in self.result.date_shifts 
        #     if shift.issue_type == 'Deliverable'
        # ]
        deliverable_shifts = self.result.date_shifts

        # Sort deliverables by key
        deliverable_shifts.sort(key=lambda x: x.issue_key)

        # Find the maximum number of shifts
        max_shifts = max((len(shift.shifts) for shift in deliverable_shifts), default=0)

        # Create row labels
        row_labels = ['Start Date'] + [f'Due Date {i+1}' for i in range(max_shifts)]
        
        # Initialize data dictionary with empty strings
        data = {
            'Row Type': row_labels
        }
        
        # Fill in data for each deliverable
        for shift in deliverable_shifts:
            column_data = []
            # Add start date
            column_data.append(shift.start_date.strftime('%Y-%m-%d %H:%M:%S %z'))
            
            # Add due dates
            sorted_shifts = sorted(shift.shifts)
            # Fill with due dates where they exist, empty strings where they don't
            for i in range(max_shifts):
                if i < len(sorted_shifts):
                    column_data.append(sorted_shifts[i].strftime('%Y-%m-%d %H:%M:%S %z'))
                else:
                    column_data.append('')
            
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
    
    def save_charts(self, output_dir: str, prefix: Optional[str] = None):
        """Save all charts and data to the specified directory."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        prefix = prefix or f"{self.result.team}_{self.result.scenario.value}"
        
        # Export the date shifts to CSV
        self.export_to_csv(output_dir, prefix)
        
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