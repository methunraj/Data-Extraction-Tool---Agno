"""
Excel Generator Agent using Agno patterns.
Converts JSON data to professional Excel files.
"""

import json
import os
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.tools.file import FileTools
from agno.tools.python import PythonTools


class ExcelGeneratorAgent(Agent):
    """
    Agent specialized in generating Excel files from JSON data.
    """

    def __init__(self, model, working_dir: Optional[str] = None):
        """Initialize Excel generator agent."""

        # Set up working directory
        work_dir = working_dir or os.environ.get("AGENT_TEMP_DIR", "/tmp/agno_work")
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        # Initialize with Python and File tools for Excel generation
        super().__init__(
            name="ExcelGenerator",
            model=model,
            tools=[
                PythonTools(
                    base_dir=Path(work_dir),
                    pip_install=True,  # Allow installing pandas/openpyxl
                    run_code=True,  # Allow running code directly
                    save_and_run=True,  # Save code to file and run it
                    run_files=True,  # Allow running saved files
                    read_files=True,  # Allow reading files
                ),
                FileTools(base_dir=Path(work_dir)),
            ],
            description="You are an expert data engineer specialized in converting JSON data to professional, well-formatted Excel files with advanced formatting, color coding, and proper data organization.",
            goal="Convert the provided JSON financial data into a professionally formatted Excel file with multiple sheets, proper headers, color coding, and intelligent data organization.",
            instructions=[
                "You are an expert at creating professional Excel reports with advanced formatting.",
                "ALWAYS start by reading and analyzing the input JSON file structure to understand the data hierarchy",
                "Detect if the JSON is wrapped in markdown format (```json\\n...\\n```)",
                "If markdown-wrapped: strip the wrapper and parse the clean JSON",
                "If pure JSON: parse directly",
                "Handle any JSON parsing errors gracefully with detailed error messages",
                "Complete ALL steps in sequence without stopping:",
                "1. Install required packages: pandas, openpyxl, and xlsxwriter using pip_install_package",
                "2. Read the complete JSON file from the provided file path using read_file",
                "3. Analyze the JSON structure deeply - understand all nested objects, arrays, and data types",
                "4. Write a comprehensive Python script using save_to_file_and_run that:",
                "   - Reads and cleans the JSON data (handle markdown wrappers)",
                "   - Creates a professional Excel workbook with these features:",
                "     * Company Overview sheet with company identification data",
                "     * Financial Metrics sheet with all metrics properly organized",
                "     * Separate sheets for different metric categories if there are many",
                "     * Summary/Dashboard sheet with key metrics highlighted",
                "     * Metadata sheet with extraction notes and data quality info",
                "   - Apply professional formatting:",
                "     * Bold headers with background colors (use corporate blue #1f4788 for headers)",
                "     * Alternate row coloring for better readability (light gray #f2f2f2)",
                "     * Number formatting for currency values (e.g., $1,234,567.89)",
                "     * Percentage formatting where applicable",
                "     * Date formatting for date fields",
                "     * Conditional formatting to highlight negative values in red",
                "     * Auto-fit column widths based on content",
                "     * Freeze panes for headers",
                "     * Add borders around data tables",
                "   - Handle data intelligently:",
                "     * Flatten nested structures (e.g., context_qualifiers arrays to comma-separated strings)",
                "     * Group related metrics together",
                "     * Sort data by year/period where applicable",
                "     * Create pivot tables or summary tables for key metrics",
                "     * Add data validation where appropriate",
                "   - Include data analysis features:",
                "     * Calculate year-over-year changes for metrics",
                "     * Add sparklines or mini charts where beneficial",
                "     * Create a summary dashboard with key KPIs",
                "     * Add filters to large data tables",
                "5. Execute the script and verify the Excel file was created successfully",
                "6. Verify the Excel file contains all expected sheets and proper formatting",
                "7. Report the file size and number of sheets created",
                "Continue with ALL steps automatically without stopping after each tool execution",
            ],
            expected_output="A professionally formatted Excel file with multiple well-organized sheets, proper color coding, headers, number formatting, and data organization. The file should look like it was created by a professional data analyst, ready for executive presentation.",
            additional_context="""The JSON contains financial data with these typical structures:
- company_identification: Basic company info (name, industry, location, etc.)
- financial_metrics: Array of metric objects with fields like:
  * metric_category (Revenue/Sales, Profitability Metrics, Balance Sheet, etc.)
  * metric_name, term_used_in_report, raw_value_string, extracted_value
  * currency, context_qualifiers (array), reporting_year, page_number, section_name
- extraction_notes: Metadata about the extraction process

Create sheets that make sense for the data:
1. Company Overview - nicely formatted company details
2. Financial Summary - key metrics dashboard
3. Revenue Metrics - all revenue-related data
4. Profitability Metrics - all profit/loss data
5. Balance Sheet Metrics - balance sheet items
6. Cash Flow Metrics - cash flow data
7. Employee Metrics - employee-related data
8. Data Quality - extraction notes and unusual findings

Use pandas with openpyxl/xlsxwriter for advanced formatting capabilities.""",
            stream=False,  # Don't stream for this focused task
            show_tool_calls=True,  # Show tool calls for debugging
            add_history_to_messages=True,  # Add chat history to messages
            num_history_responses=10,  # Keep last 10 responses in context
            exponential_backoff=True,  # Enable retry with exponential backoff
            retries=20,  # Allow up to 20 retries for better completion
            markdown=False,  # No need for markdown in this task
        )
