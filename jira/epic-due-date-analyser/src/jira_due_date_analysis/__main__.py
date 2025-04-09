"""Command-line interface for the Jira Due Date Analysis tool."""

import argparse
import logging
from pathlib import Path
import sys

from .deliverable_analyzer import DeliverableAnalyzer
from .epic_analyzer import EpicAnalyzer
from .visualizer import DueDateVisualizer
from .models import StartDateScenario
from .config import analysis_settings
from .utils import validate_date_range

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool) -> None:
    """Configure logging level and format."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description='Analyze due date shifts in Jira issues.')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create the analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze due date shifts')
    analyze_parser.add_argument(
        'issue_type',
        choices=['deliverables', 'epics'],
        help='Type of issues to analyze'
    )
    analyze_parser.add_argument(
        '--project',
        required=True,
        help='Project key (e.g., PROJ)'
    )
    analyze_parser.add_argument(
        '--team',
        required=True,
        help='Team label for filtering issues'
    )
    analyze_parser.add_argument(
        '--start-date',
        default=analysis_settings.start_date,
        help='Start date for analysis (YYYY-MM-DD)'
    )
    analyze_parser.add_argument(
        '--end-date',
        default=analysis_settings.end_date,
        help='End date for analysis (YYYY-MM-DD)'
    )
    analyze_parser.add_argument(
        '--scenario',
        type=lambda s: StartDateScenario[s.upper()],
        choices=list(StartDateScenario),
        default=StartDateScenario.FIRST_ISSUE_IN_PROGRESS,
        help='Scenario for determining start dates'
    )
    analyze_parser.add_argument(
        '--output-dir',
        default='output',
        help='Directory for saving visualization outputs'
    )
    analyze_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    analyze_parser.add_argument(
        '--show-start-dates',
        action='store_true',
        help='Show all start date markers in the visualization'
    )
    
    return parser

def validate_and_prepare_output_dir(output_dir: str) -> Path:
    """Validate and create output directory if needed."""
    path = Path(output_dir)
    if not path.exists():
        path.mkdir(parents=True)
    elif not path.is_dir():
        raise ValueError(f"{output_dir} exists but is not a directory")
    return path.resolve()

def create_analyzer(issue_type: str):
    """Create appropriate analyzer based on issue type."""
    return (
        DeliverableAnalyzer() if issue_type == 'deliverables' 
        else EpicAnalyzer()
    )

def print_analysis_summary(args, result, output_dir: Path) -> None:
    """Print summary of analysis results."""
    print("\nAnalysis Summary:")
    print(f"Analysis Type: {args.issue_type}")
    print(f"Project: {args.project}")
    print(f"Team: {args.team}")
    print(f"Scenario: {args.scenario.value}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Total issues analyzed: {len(result.date_shifts)}")
    print(f"Average number of shifts: {result.average_shifts:.1f}")
    # print(f"Average delay: {result.average_delay:.1f} days")
    print(f"\nCharts have been saved to: {output_dir}")

def run_analysis(args) -> int:
    """Run the analysis with the provided arguments."""
    # Validate and prepare
    if not args.command:
        raise ValueError("No command specified. Use 'analyze deliverables' or 'analyze epics'")
    if not validate_date_range(args.start_date, args.end_date):
        raise ValueError("Start date must be before end date")
    
    output_dir = validate_and_prepare_output_dir(args.output_dir)
    
    # Create analyzer and run analysis
    analyzer = create_analyzer(args.issue_type)
    logger.info(f"Starting {args.issue_type} analysis for project {args.project} and team {args.team}")
    
    result = analyzer.analyze_due_date_shifts(
        project_key=args.project,
        team_label=args.team,
        start_date=args.start_date,
        end_date=args.end_date,
        scenario=args.scenario,
        show_start_dates=args.show_start_dates
    )
    
    # Create and save visualizations
    visualizer = DueDateVisualizer(result)
    prefix = f"{args.project}_{args.team}_{args.issue_type}_{args.scenario.value}_{args.start_date}"
    visualizer.save_charts(str(output_dir), prefix=prefix)
    
    print_analysis_summary(args, result, output_dir)
    return 0

def main() -> int:
    """Main entry point for the application."""
    try:
        parser = create_parser()
        args = parser.parse_args()
        setup_logging(args.verbose)
        return run_analysis(args)
        
    except KeyboardInterrupt:
        logger.info(f"Analysis interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())