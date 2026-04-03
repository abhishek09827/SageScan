"""
Reporting module for SageScan validation results.

Provides multiple output formats: CLI, JSON, and HTML.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import os


class ReportFormat(Enum):
    """Supported report formats."""
    CLI = "cli"
    JSON = "json"
    HTML = "html"


@dataclass
class ValidationResult:
    """Represents a single validation result."""
    column: str
    check_type: str
    passed: bool
    message: str
    details: Dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ColumnResult:
    """Represents validation results for a single column."""
    column: str
    description: Optional[str] = None
    tags: List[str] = None
    passed: bool = True
    total_checks: int = 0
    failed_checks: int = 0
    results: List[ValidationResult] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.results is None:
            self.results = []


@dataclass
class ValidationSummary:
    """Represents the complete validation summary."""
    status: str
    context: str
    total_columns: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    pass_rate: float
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    columns: List[ColumnResult] = None
    errors: List[str] = None
    llm_explanations: Dict[str, str] = None

    def __post_init__(self):
        if self.columns is None:
            self.columns = []
        if self.errors is None:
            self.errors = []
        if self.llm_explanations is None:
            self.llm_explanations = {}


class ReportGenerator:
    """Generates reports in various formats."""
    
    def __init__(self, summary: ValidationSummary):
        self.summary = summary
    
    def generate_cli(self) -> str:
        """Generate a human-readable CLI summary using rich."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich import box
        import io

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, color_system="truecolor", width=100)

        status_color = "green" if self.summary.status == "PASS" else "red"
        title = Text(f"SageScan Validation Report: {self.summary.context or 'General'}", style="bold white")
        
        summary_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        summary_table.add_column("Key", style="cyan")
        summary_table.add_column("Value", style="bold white")
        
        summary_table.add_row("Status", Text(self.summary.status, style=f"bold {status_color}"))
        summary_table.add_row("Duration", f"{self.summary.duration_seconds:.2f}s")
        summary_table.add_row("Columns", f"{self.summary.total_columns}")
        
        checks_text = f"[green]{self.summary.passed_checks}[/green] passed / [red]{self.summary.failed_checks}[/red] failed"
        summary_table.add_row("Checks", checks_text)
        summary_table.add_row("Pass Rate", f"{self.summary.pass_rate:.1f}%")

        console.print(Panel(summary_table, title=title, border_style=status_color, padding=(1, 2)))

        if self.summary.llm_explanations:
            console.print("\n[bold magenta]🧠 AI Explanations:[/bold magenta]")
            for key, explanation in self.summary.llm_explanations.items():
                console.print(f"  [cyan]• {key}[/cyan]: {explanation}")

        if self.summary.columns:
            console.print("\n[bold white]Column Details:[/bold white]")
            columns_table = Table(box=box.ROUNDED, expand=True, header_style="bold cyan")
            columns_table.add_column("Column", style="bold white", width=25)
            columns_table.add_column("Status", width=10)
            columns_table.add_column("Failed Checks", style="red")

            for col in self.summary.columns:
                status_txt = "[green]✓ PASS[/green]" if col.passed else "[bold red]✗ FAIL[/bold red]"
                
                fails = []
                for res in col.results:
                    if not res.passed:
                        fails.append(f"{res.check_type}: {res.message}")
                
                fails_str = "\n".join(fails) if fails else "-"
                columns_table.add_row(col.column, status_txt, fails_str)
                
            console.print(columns_table)

        if self.summary.errors:
            console.print("\n[bold red]System Errors:[/bold red]")
            for err in self.summary.errors:
                console.print(f"  [red]• {err}[/red]")

        return buf.getvalue()
    
    def generate_json(self, pretty: bool = True) -> str:
        """Generate a JSON report."""
        report = {
            "summary": {
                "status": self.summary.status,
                "context": self.summary.context,
                "total_columns": self.summary.total_columns,
                "total_checks": self.summary.total_checks,
                "passed_checks": self.summary.passed_checks,
                "failed_checks": self.summary.failed_checks,
                "pass_rate": self.summary.pass_rate,
                "duration_seconds": round(self.summary.duration_seconds, 2),
                "start_time": self.summary.start_time.isoformat(),
                "end_time": self.summary.end_time.isoformat(),
            },
            "columns": [],
        }
        
        for col in self.summary.columns:
            column_data = {
                "column": col.column,
                "description": col.description,
                "tags": col.tags,
                "passed": col.passed,
                "total_checks": col.total_checks,
                "failed_checks": col.failed_checks,
                "results": [],
            }
            
            for result in col.results:
                result_data = {
                    "check_type": result.check_type,
                    "passed": result.passed,
                    "message": result.message,
                    "details": result.details,
                    "timestamp": result.timestamp,
                }
                column_data["results"].append(result_data)
            
            report["columns"].append(column_data)
        
        if self.summary.llm_explanations:
            report["explanations"] = self.summary.llm_explanations
        
        if self.summary.errors:
            report["errors"] = self.summary.errors
        
        return json.dumps(report, indent=2 if pretty else None, default=str)
    
    def generate_html(self) -> str:
        """Generate an HTML report."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SageScan Validation Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .summary {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            background: white;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }}
        .summary-item .label {{
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .summary-item .value.pass {{
            color: #27ae60;
        }}
        .summary-item .value.fail {{
            color: #c0392b;
        }}
        .column {{
            margin-bottom: 30px;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            overflow: hidden;
        }}
        .column-header {{
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .column-header .column-name {{
            font-weight: 600;
            font-size: 16px;
        }}
        .column-header .status {{
            font-size: 14px;
        }}
        .column-passed .column-header {{
            background: #27ae60;
        }}
        .column-failed .column-header {{
            background: #c0392b;
        }}
        .column-body {{
            padding: 20px;
        }}
        .column-info {{
            margin-bottom: 15px;
        }}
        .column-info p {{
            margin: 5px 0;
            color: #555;
            font-size: 14px;
        }}
        .column-info strong {{
            color: #2c3e50;
        }}
        .checks-list {{
            list-style: none;
        }}
        .check {{
            padding: 10px 15px;
            border-left: 3px solid #eee;
            margin: 5px 0;
            border-radius: 0 4px 4px 0;
        }}
        .check.passed {{
            border-left-color: #27ae60;
            background: #f0fff4;
        }}
        .check.failed {{
            border-left-color: #c0392b;
            background: #fff5f5;
        }}
        .check .check-type {{
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 3px;
        }}
        .check .check-message {{
            color: #666;
            font-size: 13px;
        }}
        .check-details {{
            margin-top: 8px;
            padding-left: 20px;
            color: #555;
            font-size: 13px;
        }}
        .explanations {{
            background: #e8f4f8;
            border: 1px solid #b8d4e3;
            border-radius: 6px;
            padding: 20px;
            margin-top: 20px;
        }}
        .explanations h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .explanation {{
            margin-bottom: 15px;
        }}
        .explanation .check-type {{
            font-weight: 600;
            color: #3498db;
        }}
        .explanation .explanation-text {{
            color: #555;
            margin-top: 5px;
            line-height: 1.6;
        }}
        .errors {{
            background: #fff5f5;
            border: 1px solid #f8d7da;
            border-radius: 6px;
            padding: 20px;
            margin-top: 20px;
        }}
        .errors h3 {{
            color: #c0392b;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .errors ul {{
            list-style: none;
        }}
        .errors li {{
            padding: 8px 0;
            border-bottom: 1px solid #f8d7da;
            color: #721c24;
        }}
        .errors li:last-child {{
            border-bottom: none;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge.pass {{
            background: #d4edda;
            color: #155724;
        }}
        .badge.fail {{
            background: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SageScan Validation Report</h1>
            <div class="meta">
                <p>Context: {self.summary.context or 'N/A'}</p>
                <p>Status: <span class="badge {'pass' if self.summary.status == 'PASS' else 'fail'}">{self.summary.status}</span></p>
                <p>Duration: {self.summary.duration_seconds:.2f}s</p>
                <p>Start: {self.summary.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>End: {self.summary.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>

        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Columns</div>
                    <div class="value">{self.summary.total_columns}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Total Checks</div>
                    <div class="value">{self.summary.total_checks}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Passed</div>
                    <div class="value pass">{self.summary.passed_checks}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Failed</div>
                    <div class="value fail">{self.summary.failed_checks}</div>
                </div>
                <div class="summary-item">
                    <div class="label">Pass Rate</div>
                    <div class="value {'pass' if self.summary.pass_rate == 100 else 'fail'}">{self.summary.pass_rate:.2f}%</div>
                </div>
            </div>
        </div>
"""
        
        # Add columns
        for col in self.summary.columns:
            status_class = 'column-passed' if col.passed else 'column-failed'
            status_badge = 'PASS' if col.passed else 'FAIL'
            
            html += f"""
        <div class="column {status_class}">
            <div class="column-header">
                <div class="column-name">{col.column}</div>
                <div class="status">{status_badge}</div>
            </div>
            <div class="column-body">
                <div class="column-info">
                    <p><strong>Description:</strong> {col.description or 'N/A'}</p>
                    <p><strong>Tags:</strong> {', '.join(col.tags) if col.tags else 'N/A'}</p>
                    <p><strong>Checks:</strong> {col.total_checks} total, {col.failed_checks} failed</p>
                </div>
                <ul class="checks-list">
"""
            
            for result in col.results:
                if result.passed:
                    html += f"""                    <li class="check passed">
                        <div class="check-type">{result.check_type}</div>
                        <div class="check-message">{result.message}</div>
                    </li>
"""
                else:
                    html += f"""                    <li class="check failed">
                        <div class="check-type">{result.check_type}</div>
                        <div class="check-message">{result.message}</div>
"""
                    if result.details:
                        html += f"""                        <div class="check-details">
                            {json.dumps(result.details, indent=4)}
                        </div>
"""
                    html += f"""                    </li>
"""
            
            html += """
                </ul>
"""
            
            # Add LLM explanations if available
            if col.column in self.summary.llm_explanations:
                html += f"""
                <div class="explanations">
                    <h3>AI Explanation</h3>
                    <div class="explanation">
                        <div class="explanation-type">{result.check_type}</div>
                        <div class="explanation-text">{self.summary.llm_explanations[col.column]}</div>
                    </div>
                </div>
"""
            
            html += """
            </div>
        </div>
"""
        
        # Add errors if any
        if self.summary.errors:
            html += f"""
        <div class="errors">
            <h3>Errors</h3>
            <ul>
"""
            for error in self.summary.errors:
                html += f"""                <li>{error}</li>
"""
            html += """
            </ul>
        </div>
"""
        
        html += """
        <div class="footer">
            <p>SageScan Validation Report • Generated on " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate(self, format: ReportFormat = ReportFormat.CLI) -> str:
        """Generate report in specified format."""
        if format == ReportFormat.CLI:
            return self.generate_cli()
        elif format == ReportFormat.JSON:
            return self.generate_json()
        elif format == ReportFormat.HTML:
            return self.generate_html()
        else:
            raise ValueError(f"Unsupported format: {format}")