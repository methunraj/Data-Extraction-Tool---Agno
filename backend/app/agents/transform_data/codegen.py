# app/agents/codegen_agent.py
import os
import logging
from pathlib import Path
from typing import Optional, Dict

from agno.agent import Agent
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.storage.sqlite import SqliteStorage

from ..base import BaseAgent
from ...core.config import settings

logger = logging.getLogger(__name__)


class CodeGenAgent(BaseAgent):
    """Python execution agent for Excel generation with comprehensive tools."""
    
    def __init__(self, temp_dir: str, exchange_rates: Optional[Dict[str, float]] = None, model_id=None):
        super().__init__("codegen", temp_dir, model_id=model_id)
        self.exchange_rates = exchange_rates
        if not temp_dir:
            raise ValueError("temp_dir is required for codegen agent")
        
        # Validate environment on initialization
        if not self.validate_environment():
            raise RuntimeError(f"Environment validation failed for temp_dir: {temp_dir}")
    
    def validate_environment(self) -> bool:
        """Validate the execution environment before running"""
        try:
            # Ensure directory exists
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Test file creation
            test_file = os.path.join(self.temp_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Test file reading
            with open(test_file, 'r') as f:
                content = f.read()
                if content != 'test':
                    raise ValueError("File read/write test failed")
            
            # Clean up test file
            os.remove(test_file)
            
            # Check permissions
            if not os.access(self.temp_dir, os.W_OK):
                raise PermissionError(f"No write access to {self.temp_dir}")
            
            if not os.access(self.temp_dir, os.R_OK):
                raise PermissionError(f"No read access to {self.temp_dir}")
            
            logger.info(f"Environment validation passed for: {self.temp_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return False
    
    def get_file_operations_code(self) -> str:
        """Generate reliable file operation code"""
        abs_temp_dir = os.path.abspath(self.temp_dir)
        return f'''
import os
import sys
import shutil

class FileOperations:
    OUTPUT_DIR = r'{abs_temp_dir}'
    
    @classmethod
    def save_excel(cls, wb, filename='financial_report.xlsx'):
        """Reliably save Excel file to correct location"""
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(cls.OUTPUT_DIR, filename)
        
        # Try primary save
        try:
            wb.save(filepath)
            print(f'✅ Saved to: {{filepath}}')
            if cls.verify_file(filepath):
                return filepath
        except Exception as e:
            print(f'⚠️ Primary save failed: {{e}}')
        
        # Fallback: try alternative filename
        try:
            alt_filename = f'backup_{{filename}}'
            alt_filepath = os.path.join(cls.OUTPUT_DIR, alt_filename)
            wb.save(alt_filepath)
            print(f'✅ Saved via fallback to: {{alt_filepath}}')
            if cls.verify_file(alt_filepath):
                return alt_filepath
        except Exception as e:
            print(f'⚠️ Fallback save failed: {{e}}')
        
        # Last resort: save to current directory then move
        try:
            temp_path = os.path.abspath(filename)
            wb.save(temp_path)
            final_path = os.path.join(cls.OUTPUT_DIR, filename)
            shutil.move(temp_path, final_path)
            print(f'✅ Saved via move operation to: {{final_path}}')
            if cls.verify_file(final_path):
                return final_path
        except Exception as e:
            print(f'❌ All save attempts failed: {{e}}')
            raise
    
    @classmethod
    def verify_file(cls, filepath):
        """Verify file was created successfully"""
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f'✅ File verified: {{filepath}} ({{size}} bytes)')
            return size > 0
        else:
            print(f'❌ File not found: {{filepath}}')
            # List directory contents for debugging
            try:
                contents = os.listdir(cls.OUTPUT_DIR)
                print(f'Directory contents: {{contents}}')
            except Exception as e:
                print(f'Could not list directory: {{e}}')
            return False
    
    @classmethod
    def get_working_directory(cls):
        """Get current working directory for debugging"""
        cwd = os.getcwd()
        print(f'Current working directory: {{cwd}}')
        print(f'Target output directory: {{cls.OUTPUT_DIR}}')
        print(f'Directories match: {{cwd == cls.OUTPUT_DIR}}')
        return cwd

# Use this class for all file operations
'''
    
    def get_instructions(self) -> list:
        """Get code generation agent specific instructions."""
        # Force absolute path usage
        abs_temp_dir = os.path.abspath(self.temp_dir)
        
        # Build exchange rate instructions if provided
        exchange_rate_info = ""
        if self.exchange_rates:
            exchange_rate_info = "\n## EXCHANGE RATES PROVIDED:\n"
            for currency, rate in self.exchange_rates.items():
                exchange_rate_info += f"- 1 {currency} = {rate} USD\n"
        
        return [
            "Create an Excel report from the provided JSON data.",
            f"CRITICAL: Save ALL files to this EXACT path: {abs_temp_dir}",
            "Use the save_to_file_and_run tool to execute Python code.",
            "Analyze the input data and create meaningful sheets, headers, and formatting based on the data structure.",
            exchange_rate_info,  # Include exchange rates if available
            "",
            "MANDATORY FIRST STEP - Run this diagnostic and setup code:",
            "```python",
            "import os",
            "import sys",
            "print('=== DIAGNOSTICS ===')",
            "print(f'Current Working Directory: {os.getcwd()}')",
            "print(f'Python Executable: {sys.executable}')",
            f"target_dir = r'{abs_temp_dir}'",
            "print(f'Target Directory: {os.path.abspath(target_dir)}')",
            "print(f'Target Dir Exists: {os.path.exists(target_dir)}')",
            "print('===================')",
            "",
            f"OUTPUT_DIR = r'{abs_temp_dir}'",
            "os.makedirs(OUTPUT_DIR, exist_ok=True)",
            "os.chdir(OUTPUT_DIR)",
            "print(f'Working in: {os.getcwd()}')",
            "```",
            "",
            "Steps:",
            "1. Use save_to_file_and_run to create Python code with FileOperations class",
            "2. Import openpyxl and create a workbook", 
            "3. Add the JSON data to Excel sheets",
            "4. Use FileOperations.save_excel() to save reliably",
            "5. Verify file creation with FileOperations.verify_file()",
            "",
            "MANDATORY: Use this FileOperations class for reliable file handling:",
            self.get_file_operations_code(),
            "",
            "Example code structure:",
            "```python",
            "import openpyxl",
            "import os",
            "",
            "# Use the FileOperations class defined above",
            "",
            "# Create workbook",
            "wb = openpyxl.Workbook()",
            "ws = wb.active",
            "",
            "# Add data to sheet",
            "# ... add your data here ...",
            "",
            "# Save file using reliable FileOperations",
            "try:",
            "    filepath = FileOperations.save_excel(wb, 'financial_report.xlsx')",
            "    print(f'✅ Successfully saved: {filepath}')",
            "    ",
            "    # Verify the file",
            "    if FileOperations.verify_file(filepath):",
            "        print('✅ File verification passed')",
            "    else:",
            "        print('❌ File verification failed')",
            "        ",
            "except Exception as e:",
            "    print(f'❌ File save failed: {e}')",
            "    # Debug information",
            "    FileOperations.get_working_directory()",
            "```",
            "",
            "Use the save_to_file_and_run tool now to execute this code."
        ]
    
    def get_tools(self) -> list:
        """Code generation agent has comprehensive Python and Shell tools."""
        abs_temp_dir = Path(self.temp_dir).absolute()
        
        # Ensure directory exists before agent uses it
        abs_temp_dir.mkdir(parents=True, exist_ok=True)
        
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
                base_dir=abs_temp_dir,
                
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