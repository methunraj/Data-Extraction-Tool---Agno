# app/agents/codegen_agent.py
import os
from pathlib import Path
from typing import Optional, Dict

from agno.agent import Agent
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.storage.sqlite import SqliteStorage

from ..base import BaseAgent
from ...core.config import settings


class CodeGenAgent(BaseAgent):
    """Python execution agent for Excel generation with comprehensive tools."""
    
    def __init__(self, temp_dir: str, exchange_rates: Optional[Dict[str, float]] = None, model_id=None):
        super().__init__("codegen", temp_dir, model_id=model_id)
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
            "Create an Excel report from the provided JSON data.",
            f"Save the Excel file to this directory: {self.temp_dir}",
            f"Use the save_to_file_and_run tool to execute Python code.",
            "Analyze the input data and create meaningful sheets, headers, and formatting based on the data structure.",
            exchange_rate_info,  # Include exchange rates if available
            "",
            "Steps:",
            "1. Use save_to_file_and_run to create Python code",
            "2. Import openpyxl and create a workbook", 
            "3. Add the JSON data to Excel sheets",
            "4. Save the file and verify it exists",
            "",
            "Example code structure:",
            "```python",
            "import openpyxl",
            "import os",
            "",
            "# Create workbook",
            "wb = openpyxl.Workbook()",
            "ws = wb.active",
            "",
            "# Add data to sheet",
            "# ... add your data here ...",
            "",
            f"# Save file",
            f"filepath = os.path.join(r'{self.temp_dir}', 'financial_report.xlsx')",
            "wb.save(filepath)",
            "print(f'File saved: {filepath}')",
            "print(f'File exists: {os.path.exists(filepath)}')",
            "```",
            "",
            "Use the save_to_file_and_run tool now to execute this code."
        ]
    
    def get_tools(self) -> list:
        """Code generation agent has comprehensive Python and Shell tools."""
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
            ShellTools(),  # For system-level debugging and file operations
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