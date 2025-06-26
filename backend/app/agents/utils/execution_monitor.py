import time
import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ExecutionRecord:
    """Record of an agent execution"""
    timestamp: float
    agent_type: str
    temp_dir: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    files_created: List[str] = None
    
    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []

class AgentExecutionMonitor:
    """Monitor agent execution and file operations"""
    
    def __init__(self):
        self.executions: List[ExecutionRecord] = []
        self._start_times: Dict[str, float] = {}
    
    def start_execution(self, execution_id: str, agent_type: str, temp_dir: str) -> str:
        """Start monitoring an execution"""
        self._start_times[execution_id] = time.time()
        logger.info(f"Started monitoring execution {execution_id} for {agent_type} in {temp_dir}")
        return execution_id
    
    def end_execution(self, execution_id: str, agent_type: str, temp_dir: str, 
                     success: bool, details: Dict[str, Any], 
                     error_message: Optional[str] = None) -> ExecutionRecord:
        """End monitoring and record execution details"""
        start_time = self._start_times.pop(execution_id, time.time())
        duration = time.time() - start_time
        
        # Find files created in temp_dir
        files_created = []
        if os.path.exists(temp_dir):
            try:
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path) and file.endswith('.xlsx'):
                        files_created.append(file_path)
            except Exception as e:
                logger.warning(f"Could not list files in {temp_dir}: {e}")
        
        record = ExecutionRecord(
            timestamp=time.time(),
            agent_type=agent_type,
            temp_dir=temp_dir,
            success=success,
            duration=duration,
            details=details,
            error_message=error_message,
            files_created=files_created
        )
        
        self.executions.append(record)
        logger.info(f"Recorded execution {execution_id}: success={success}, duration={duration:.2f}s, files={len(files_created)}")
        
        return record
    
    def record_execution(self, agent_type: str, temp_dir: str, success: bool, 
                        details: Dict[str, Any], error_message: Optional[str] = None) -> ExecutionRecord:
        """Record execution details for analysis (legacy method)"""
        record = ExecutionRecord(
            timestamp=time.time(),
            agent_type=agent_type,
            temp_dir=temp_dir,
            success=success,
            duration=0.0,  # Unknown duration
            details=details,
            error_message=error_message,
            files_created=[]
        )
        
        self.executions.append(record)
        return record
    
    def get_failure_patterns(self) -> Dict[str, Any]:
        """Analyze failures to identify patterns"""
        failures = [e for e in self.executions if not e.success]
        total_executions = len(self.executions)
        
        if not failures:
            return {
                'total_executions': total_executions,
                'total_failures': 0,
                'failure_rate': 0.0,
                'patterns': {}
            }
        
        # Analyze failure patterns
        directory_issues = 0
        permission_issues = 0
        file_not_found_issues = 0
        timeout_issues = 0
        
        common_paths = {}
        error_types = {}
        
        for failure in failures:
            error_msg = failure.error_message or failure.details.get('error', '')
            error_lower = error_msg.lower()
            
            # Count issue types
            if 'directory' in error_lower or 'path' in error_lower:
                directory_issues += 1
            if 'permission' in error_lower or 'access' in error_lower:
                permission_issues += 1
            if 'not found' in error_lower or 'no such file' in error_lower:
                file_not_found_issues += 1
            if 'timeout' in error_lower or 'time' in error_lower:
                timeout_issues += 1
            
            # Track common failure paths
            temp_dir = failure.temp_dir
            if temp_dir in common_paths:
                common_paths[temp_dir] += 1
            else:
                common_paths[temp_dir] = 1
            
            # Track error types
            error_key = error_msg[:50] if error_msg else 'unknown'
            if error_key in error_types:
                error_types[error_key] += 1
            else:
                error_types[error_key] = 1
        
        return {
            'total_executions': total_executions,
            'total_failures': len(failures),
            'failure_rate': len(failures) / total_executions if total_executions > 0 else 0.0,
            'patterns': {
                'directory_issues': directory_issues,
                'permission_issues': permission_issues,
                'file_not_found_issues': file_not_found_issues,
                'timeout_issues': timeout_issues
            },
            'common_failure_paths': dict(sorted(common_paths.items(), key=lambda x: x[1], reverse=True)[:5]),
            'common_error_types': dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def get_success_metrics(self) -> Dict[str, Any]:
        """Get success metrics and performance data"""
        if not self.executions:
            return {'no_data': True}
        
        successes = [e for e in self.executions if e.success]
        total = len(self.executions)
        
        # Calculate metrics
        success_rate = len(successes) / total if total > 0 else 0.0
        
        # Duration statistics
        durations = [e.duration for e in self.executions if e.duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        # Files created statistics
        total_files = sum(len(e.files_created) for e in successes)
        avg_files_per_execution = total_files / len(successes) if successes else 0.0
        
        # Recent performance (last 10 executions)
        recent_executions = self.executions[-10:] if len(self.executions) >= 10 else self.executions
        recent_success_rate = len([e for e in recent_executions if e.success]) / len(recent_executions) if recent_executions else 0.0
        
        return {
            'total_executions': total,
            'success_rate': success_rate,
            'recent_success_rate': recent_success_rate,
            'average_duration': avg_duration,
            'total_files_created': total_files,
            'average_files_per_execution': avg_files_per_execution,
            'agent_type_breakdown': self._get_agent_type_breakdown()
        }
    
    def _get_agent_type_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown by agent type"""
        breakdown = {}
        
        for execution in self.executions:
            agent_type = execution.agent_type
            if agent_type not in breakdown:
                breakdown[agent_type] = {
                    'total': 0,
                    'successes': 0,
                    'failures': 0,
                    'avg_duration': 0.0
                }
            
            breakdown[agent_type]['total'] += 1
            if execution.success:
                breakdown[agent_type]['successes'] += 1
            else:
                breakdown[agent_type]['failures'] += 1
        
        # Calculate success rates and average durations
        for agent_type, stats in breakdown.items():
            stats['success_rate'] = stats['successes'] / stats['total'] if stats['total'] > 0 else 0.0
            
            # Calculate average duration for this agent type
            durations = [e.duration for e in self.executions 
                        if e.agent_type == agent_type and e.duration > 0]
            stats['avg_duration'] = sum(durations) / len(durations) if durations else 0.0
        
        return breakdown
    
    def export_data(self) -> List[Dict[str, Any]]:
        """Export execution data for analysis"""
        return [asdict(record) for record in self.executions]
    
    def clear_old_records(self, max_age_hours: int = 24):
        """Clear old execution records"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        initial_count = len(self.executions)
        
        self.executions = [e for e in self.executions if e.timestamp > cutoff_time]
        
        removed_count = initial_count - len(self.executions)
        if removed_count > 0:
            logger.info(f"Cleared {removed_count} old execution records (older than {max_age_hours} hours)")

# Global monitor instance
execution_monitor = AgentExecutionMonitor()