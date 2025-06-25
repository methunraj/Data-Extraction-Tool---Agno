# app/agents/codegen_agent.py
import os
from pathlib import Path
from typing import Optional, Dict

from agno.agent import Agent
from agno.tools.python import PythonTools
from agno.storage.sqlite import SqliteStorage

from .base import BaseAgent
from ..core.config import settings


class CodeGenAgent(BaseAgent):
    """Python execution agent for Excel generation with comprehensive tools."""
    
    def __init__(self, temp_dir: str, exchange_rates: Optional[Dict[str, float]] = None):
        super().__init__("codegen", temp_dir)
        self.exchange_rates = exchange_rates
        if not temp_dir:
            raise ValueError("temp_dir is required for codegen agent")
    
    def get_instructions(self) -> list:
        """Get code generation agent specific instructions."""
        # Build exchange rate instructions if provided
        exchange_rate_info = ""
        if self.exchange_rates:
            exchange_rate_info = "\n## EXCHANGE RATES PROVIDED:\n"
            for currency, rate in self.exchange_rates.items():
                exchange_rate_info += f"- 1 {currency} = {rate} USD\n"
        
        return [
            "You are a senior financial analyst. Create a COMPREHENSIVE multi-sheet Excel report with structured data tables and meaningful narratives.",
            "Save and run a Python script named 'excel_report_generator.py' and EXECUTE it immediately using your Python tools.",
            exchange_rate_info,  # Include exchange rates if available
            "",
            f"## CRITICAL: FILE SAVING LOCATION",
            f"- MANDATORY: Save Excel files to this EXACT path: {self.temp_dir}",
            f"- Example: workbook.save(r'{self.temp_dir}\\report.xlsx')",
            f"- Always use the full path when saving: os.path.join(r'{self.temp_dir}', 'filename.xlsx')",
            f"- After saving, verify file exists with: os.path.exists(filepath)",
            f"- Print the full file path after saving to confirm location",
            "",
            "## CODE EXECUTION REQUIREMENTS:",
            "- You MUST execute the Python code using your save_to_file_and_run tool",
            "- Don't just show code - RUN it to create the actual Excel file",
            "- Use your Python tools to execute the script and generate the Excel file",
            "- Verify the Excel file was created by checking if it exists",
            "",
            "## TECHNICAL REQUIREMENTS:",
            "Import required libraries: os, openpyxl, openpyxl.styles, openpyxl.formatting",
            "Keep code modular and well-documented",
            "",
            "## ERROR HANDLING - CRITICAL:",
            "If any code execution fails, you MUST:",
            "1. Read the error message carefully",
            "2. Identify the root cause (e.g. data structure issues, missing imports)",
            "3. Fix the code immediately", 
            "4. Save and run the corrected code",
            "5. Repeat until Excel file is successfully created with ALL enhancements",
            "REMEMBER: You have run_files=True so you can execute Python files directly",
            "DO NOT GIVE UP - keep trying until the Excel file exists with structured data and complete data analysis",
            "",
            "## QUALITY STANDARDS:",
            "- Every sheet must have professional table formatting",
            "- All numerical data must be properly formatted (currency, percentages)",
            "- Tables must have proper headers and organized structure",
            "- Include data validation and error checking tables",
            "- Ensure all source data is captured and analyzed in tabular format",
            "- Create a comprehensive table of contents on the first sheet"
        ]
    
    def get_tools(self) -> list:
        """Code generation agent has comprehensive Python tools."""
        return [
            PythonTools(
                # Core execution settings
                run_code=True, 
                pip_install=True, 
                save_and_run=True, 
                read_files=True,
                list_files=True,
                run_files=True,
                
                # Directory configuration
                base_dir=Path(self.temp_dir).absolute(),
                
                # Performance optimizations
                safe_globals=None,
                safe_locals=None,
            ),
        ]
    
    def create_agent(self) -> Agent:
        """Create the code generation agent with enhanced configuration."""
        if self._agent is not None:
            return self._agent
        
        # Create unique storage for Python agent
        storage_dir = Path("storage")
        storage_dir.mkdir(exist_ok=True)
        unique_db_id = os.urandom(4).hex()
        db_path = storage_dir / f"python_agents_{unique_db_id}.db"
        
        # Ensure storage directory has write permissions
        storage_dir.chmod(0o755)
        
        agent_storage = SqliteStorage(
            table_name="python_agent_sessions",
            db_file=str(db_path),
            auto_upgrade_schema=True
        )
        
        # Ensure database file has write permissions
        if db_path.exists():
            db_path.chmod(0o644)
        
        # Create Python execution agent with enhanced configuration
        self._agent = Agent(
            model=self.create_gemini_model(),
            tools=self.get_tools(),
            storage=agent_storage,
            add_history_to_messages=True,
            num_history_runs=3,
            reasoning=False,
            show_tool_calls=True,
            markdown=True,
            add_datetime_to_instructions=True,
            tool_call_limit=20,
            instructions=self.get_instructions(),
            exponential_backoff=True,
            retries=5,
            debug_mode=settings.AGNO_DEBUG,
            monitoring=settings.AGNO_MONITOR,
        )
        
        return self._agent