import os
import ast
import re
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from .execution_context import AgentExecutionContext
from .config_manager import config_manager

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Result of a validation check"""
    level: ValidationLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None

class ValidationRule:
    """Base class for validation rules"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def validate(self, context: AgentExecutionContext, code: str) -> List[ValidationResult]:
        """Validate code against this rule"""
        raise NotImplementedError

class SecurityValidationRule(ValidationRule):
    """Validate code for security issues"""
    
    def __init__(self):
        super().__init__("security", "Check for security vulnerabilities")
        
        # Dangerous patterns to look for
        self.dangerous_patterns = [
            (r'subprocess\.', "Subprocess execution detected"),
            (r'os\.system\(', "OS system call detected"),
            (r'eval\(', "eval() function detected"),
            (r'exec\(', "exec() function detected"),
            (r'__import__\(', "Dynamic import detected"),
            (r'open\([\'"][^\'"]*(\.\.\/|\/etc\/|\/proc\/)', "Suspicious file access"),
            (r'rm\s+-rf', "Dangerous file deletion command"),
            (r'chmod\s+777', "Dangerous permission change"),
        ]
    
    def validate(self, context: AgentExecutionContext, code: str) -> List[ValidationResult]:
        results = []
        
        for pattern, message in self.dangerous_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                results.append(ValidationResult(
                    level=ValidationLevel.CRITICAL,
                    message=f"Security issue: {message}",
                    details={
                        "pattern": pattern,
                        "match": match.group(),
                        "position": match.span()
                    },
                    suggestion="Remove or replace with safer alternative"
                ))
        
        return results

class ImportValidationRule(ValidationRule):
    """Validate imports against allowed list"""
    
    def __init__(self):
        super().__init__("imports", "Check for allowed imports")
    
    def validate(self, context: AgentExecutionContext, code: str) -> List[ValidationResult]:
        results = []
        
        # Get allowed imports from config
        agent_type = context.metadata.get('agent_type', 'unknown')
        config = config_manager.get_agent_config(agent_type)
        allowed_imports = set(config.allowed_imports)
        
        try:
            # Parse code to extract imports
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]  # Get top-level module
                        if module_name not in allowed_imports:
                            results.append(ValidationResult(
                                level=ValidationLevel.ERROR,
                                message=f"Disallowed import: {alias.name}",
                                details={
                                    "module": alias.name,
                                    "line": node.lineno
                                },
                                suggestion=f"Use one of allowed imports: {', '.join(sorted(allowed_imports))}"
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name not in allowed_imports:
                            results.append(ValidationResult(
                                level=ValidationLevel.ERROR,
                                message=f"Disallowed import from: {node.module}",
                                details={
                                    "module": node.module,
                                    "line": node.lineno
                                },
                                suggestion=f"Use one of allowed imports: {', '.join(sorted(allowed_imports))}"
                            ))
        
        except SyntaxError as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"Syntax error in code: {e}",
                details={"error": str(e)},
                suggestion="Fix syntax errors before execution"
            ))
        
        return results

class FileOperationValidationRule(ValidationRule):
    """Validate file operations are within allowed directories"""
    
    def __init__(self):
        super().__init__("file_operations", "Check file operations are within bounds")
    
    def validate(self, context: AgentExecutionContext, code: str) -> List[ValidationResult]:
        results = []
        
        # Patterns that indicate file operations
        file_patterns = [
            (r'open\s*\(\s*[\'"]([^\'"]+)[\'"]', "File open operation"),
            (r'\.to_excel\s*\(\s*[\'"]([^\'"]+)[\'"]', "Excel file write"),
            (r'\.save\s*\(\s*[\'"]([^\'"]+)[\'"]', "File save operation"),
            (r'os\.path\.join\s*\([^)]*[\'"]([^\'"]+)[\'"]', "Path construction"),
        ]
        
        temp_dir = context.temp_dir
        
        for pattern, operation_type in file_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                file_path = match.group(1)
                
                # Check if path is absolute and outside temp directory
                if os.path.isabs(file_path) and not file_path.startswith(temp_dir):
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        message=f"{operation_type} outside temp directory: {file_path}",
                        details={
                            "file_path": file_path,
                            "temp_dir": temp_dir,
                            "operation": operation_type
                        },
                        suggestion=f"Use paths within temp directory: {temp_dir}"
                    ))
                
                # Check for suspicious paths
                suspicious_paths = ['/etc/', '/proc/', '/sys/', '/dev/', '..']
                if any(suspicious in file_path for suspicious in suspicious_paths):
                    results.append(ValidationResult(
                        level=ValidationLevel.CRITICAL,
                        message=f"Suspicious file path: {file_path}",
                        details={
                            "file_path": file_path,
                            "operation": operation_type
                        },
                        suggestion="Use only safe file paths within the working directory"
                    ))
        
        return results

class ResourceValidationRule(ValidationRule):
    """Validate resource usage patterns"""
    
    def __init__(self):
        super().__init__("resources", "Check for resource usage patterns")
    
    def validate(self, context: AgentExecutionContext, code: str) -> List[ValidationResult]:
        results = []
        
        # Check for potential memory issues
        memory_patterns = [
            (r'\.read\(\)', "Reading entire file into memory"),
            (r'pd\.read_csv\([^)]*\)', "Reading CSV file"),
            (r'pd\.read_excel\([^)]*\)', "Reading Excel file"),
            (r'range\(\s*\d{6,}\s*\)', "Large range operation"),
        ]
        
        for pattern, description in memory_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    message=f"Potential memory usage: {description}",
                    details={
                        "pattern": match.group(),
                        "line_context": match.group()
                    },
                    suggestion="Consider chunked processing for large data"
                ))
        
        # Check for infinite loops
        loop_patterns = [
            (r'while\s+True\s*:', "Infinite while loop"),
            (r'for\s+\w+\s+in\s+itertools\.count\(\)', "Infinite iterator"),
        ]
        
        for pattern, description in loop_patterns:
            if re.search(pattern, code):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"Potential infinite loop: {description}",
                    suggestion="Ensure loop has proper exit conditions"
                ))
        
        return results

class ExecutionValidator:
    """Main validation framework for agent execution"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = [
            SecurityValidationRule(),
            ImportValidationRule(),
            FileOperationValidationRule(),
            ResourceValidationRule(),
        ]
        self.custom_rules: List[ValidationRule] = []
    
    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule"""
        self.custom_rules.append(rule)
        logger.info(f"Added custom validation rule: {rule.name}")
    
    def validate_code(self, context: AgentExecutionContext, code: str) -> Dict[str, Any]:
        """Validate code against all rules"""
        all_results = []
        rule_results = {}
        
        # Run all built-in rules
        for rule in self.rules + self.custom_rules:
            try:
                results = rule.validate(context, code)
                rule_results[rule.name] = results
                all_results.extend(results)
                
            except Exception as e:
                logger.error(f"Validation rule {rule.name} failed: {e}")
                all_results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    message=f"Validation rule error: {rule.name}",
                    details={"error": str(e)}
                ))
        
        # Categorize results by level
        categorized = {level.value: [] for level in ValidationLevel}
        for result in all_results:
            categorized[result.level.value].append(result)
        
        # Determine overall validation status
        has_critical = len(categorized['critical']) > 0
        has_errors = len(categorized['error']) > 0
        
        if has_critical:
            status = "blocked"
        elif has_errors:
            status = "warning"
        else:
            status = "passed"
        
        return {
            'status': status,
            'total_issues': len(all_results),
            'by_level': {
                level: len(results) for level, results in categorized.items()
            },
            'results': categorized,
            'rule_results': rule_results,
            'context_session': context.session_id,
            'code_length': len(code)
        }
    
    def validate_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """Validate execution context"""
        issues = context.validate_context()
        
        # Additional context validations
        agent_type = context.metadata.get('agent_type', 'unknown')
        config_issues = config_manager.validate_config(agent_type)
        
        all_issues = issues + config_issues
        
        return {
            'status': 'passed' if not all_issues else 'failed',
            'issues': all_issues,
            'context_valid': len(issues) == 0,
            'config_valid': len(config_issues) == 0,
            'session_id': context.session_id
        }
    
    def get_validation_summary(self, context: AgentExecutionContext, code: str) -> Dict[str, Any]:
        """Get comprehensive validation summary"""
        context_validation = self.validate_context(context)
        code_validation = self.validate_code(context, code)
        
        overall_status = "passed"
        if context_validation['status'] == 'failed' or code_validation['status'] == 'blocked':
            overall_status = "blocked"
        elif code_validation['status'] == 'warning':
            overall_status = "warning"
        
        return {
            'overall_status': overall_status,
            'context_validation': context_validation,
            'code_validation': code_validation,
            'timestamp': context.created_at,
            'session_id': context.session_id
        }

# Global validator instance
execution_validator = ExecutionValidator()