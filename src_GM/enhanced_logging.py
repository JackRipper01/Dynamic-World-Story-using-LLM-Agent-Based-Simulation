"""
Enhanced logging system for Dynamic World Story Simulation
Provides structured logging, error handling, and performance monitoring.
"""

import logging
import sys
import os
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from functools import wraps

try:
    from rich.logging import RichHandler
    from rich.console import Console
    from rich.traceback import install as install_rich_traceback
    RICH_AVAILABLE = True
    install_rich_traceback()
except ImportError:
    RICH_AVAILABLE = False
    RichHandler = None
    Console = None


class SimulationLogger:
    """Enhanced logger for simulation events and debugging"""
    
    def __init__(self, name: str = "simulation", log_level: str = "INFO", 
                 log_file: Optional[str] = None, enable_rich: bool = True):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        if RICH_AVAILABLE and enable_rich:
            console_handler = RichHandler(rich_tracebacks=True)
            console_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
            )
            self.logger.addHandler(file_handler)
        
        # Performance tracking
        self.performance_data = {}
        self.start_time = time.time()
        
        # Error tracking
        self.error_count = 0
        self.warning_count = 0
        
        self.info("Logger initialized", extra={"component": "logging"})
    
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data"""
        self.logger.debug(self._format_message(message, kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data"""
        self.logger.info(self._format_message(message, kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data"""
        self.warning_count += 1
        self.logger.warning(self._format_message(message, kwargs))
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception and structured data"""
        self.error_count += 1
        if exception:
            kwargs['exception_type'] = type(exception).__name__
            kwargs['exception_message'] = str(exception)
            self.logger.error(self._format_message(message, kwargs), exc_info=exception)
        else:
            self.logger.error(self._format_message(message, kwargs))
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message with optional exception and structured data"""
        self.error_count += 1
        if exception:
            kwargs['exception_type'] = type(exception).__name__
            kwargs['exception_message'] = str(exception)
            self.logger.critical(self._format_message(message, kwargs), exc_info=exception)
        else:
            self.logger.critical(self._format_message(message, kwargs))
    
    def _format_message(self, message: str, extra_data: Dict[str, Any]) -> str:
        """Format message with structured data"""
        if not extra_data:
            return message
        
        # Extract common fields
        component = extra_data.pop('component', None)
        agent = extra_data.pop('agent', None)
        step = extra_data.pop('step', None)
        
        # Build prefix
        prefix_parts = []
        if component:
            prefix_parts.append(f"[{component}]")
        if agent:
            prefix_parts.append(f"Agent:{agent}")
        if step is not None:
            prefix_parts.append(f"Step:{step}")
        
        prefix = " ".join(prefix_parts)
        if prefix:
            message = f"{prefix} {message}"
        
        # Add remaining data as JSON if present
        if extra_data:
            try:
                data_str = json.dumps(extra_data, default=str)
                message += f" | Data: {data_str}"
            except (TypeError, ValueError):
                message += f" | Data: {extra_data}"
        
        return message
    
    @contextmanager
    def performance_timer(self, operation_name: str):
        """Context manager for timing operations"""
        start_time = time.time()
        self.debug(f"Starting {operation_name}", component="performance")
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.performance_data[operation_name] = self.performance_data.get(operation_name, [])
            self.performance_data[operation_name].append(duration)
            
            self.info(f"Completed {operation_name}", 
                     component="performance", 
                     duration=f"{duration:.3f}s")
    
    def log_agent_action(self, agent_name: str, action: str, step: int, 
                        location: str, success: bool = True, **kwargs):
        """Specialized logging for agent actions"""
        status = "SUCCESS" if success else "FAILED"
        self.info(f"Agent action {status}: {action}", 
                 component="agent_action",
                 agent=agent_name,
                 step=step,
                 location=location,
                 **kwargs)
    
    def log_world_event(self, event_description: str, location: str, 
                       step: int, triggered_by: str = None, **kwargs):
        """Specialized logging for world events"""
        self.info(f"World event: {event_description}",
                 component="world_event",
                 location=location,
                 step=step,
                 triggered_by=triggered_by,
                 **kwargs)
    
    def log_llm_call(self, model_name: str, purpose: str, 
                    input_tokens: int = None, output_tokens: int = None,
                    duration: float = None, **kwargs):
        """Specialized logging for LLM API calls"""
        self.info(f"LLM call: {purpose}",
                 component="llm_call",
                 model=model_name,
                 input_tokens=input_tokens,
                 output_tokens=output_tokens,
                 duration=f"{duration:.3f}s" if duration else None,
                 **kwargs)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance statistics summary"""
        summary = {
            'total_runtime': time.time() - self.start_time,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'operations': {}
        }
        
        for operation, durations in self.performance_data.items():
            summary['operations'][operation] = {
                'count': len(durations),
                'total_time': sum(durations),
                'avg_time': sum(durations) / len(durations),
                'min_time': min(durations),
                'max_time': max(durations)
            }
        
        return summary
    
    def log_performance_summary(self):
        """Log a summary of performance statistics"""
        summary = self.get_performance_summary()
        
        self.info("=== PERFORMANCE SUMMARY ===", component="performance")
        self.info(f"Total runtime: {summary['total_runtime']:.3f}s", component="performance")
        self.info(f"Errors: {summary['error_count']}, Warnings: {summary['warning_count']}", 
                 component="performance")
        
        for operation, stats in summary['operations'].items():
            self.info(f"{operation}: {stats['count']} calls, "
                     f"avg {stats['avg_time']:.3f}s, "
                     f"total {stats['total_time']:.3f}s",
                     component="performance")


class ErrorHandler:
    """Enhanced error handling with recovery strategies"""
    
    def __init__(self, logger: SimulationLogger):
        self.logger = logger
        self.error_history = []
        self.recovery_strategies = {}
    
    def register_recovery_strategy(self, error_type: type, strategy_func):
        """Register a recovery strategy for a specific error type"""
        self.recovery_strategies[error_type] = strategy_func
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """Handle an error with potential recovery
        
        Returns:
            bool: True if error was recovered from, False otherwise
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        self.error_history.append(error_info)
        
        # Log the error
        self.logger.error(f"Error occurred: {error}", 
                         exception=error,
                         context=context)
        
        # Try recovery strategy
        error_type = type(error)
        if error_type in self.recovery_strategies:
            try:
                self.logger.info(f"Attempting recovery for {error_type.__name__}")
                recovery_result = self.recovery_strategies[error_type](error, context)
                
                if recovery_result:
                    self.logger.info(f"Successfully recovered from {error_type.__name__}")
                    return True
                else:
                    self.logger.warning(f"Recovery failed for {error_type.__name__}")
            except Exception as recovery_error:
                self.logger.error(f"Recovery strategy failed", 
                                exception=recovery_error)
        
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered"""
        if not self.error_history:
            return {'total_errors': 0, 'error_types': {}}
        
        error_types = {}
        for error_info in self.error_history:
            error_type = error_info['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'error_types': error_types,
            'recent_errors': self.error_history[-5:]  # Last 5 errors
        }


def with_error_handling(logger: SimulationLogger, error_handler: ErrorHandler = None):
    """Decorator for automatic error handling and logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                with logger.performance_timer(func.__name__):
                    return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:200],  # Truncate long args
                    'kwargs': str(kwargs)[:200]
                }
                
                if error_handler:
                    recovered = error_handler.handle_error(e, context)
                    if not recovered:
                        raise
                else:
                    logger.error(f"Error in {func.__name__}", exception=e, **context)
                    raise
        
        return wrapper
    return decorator


def setup_simulation_logging(log_level: str = "INFO", 
                           log_file: Optional[str] = None,
                           enable_rich: bool = True) -> tuple[SimulationLogger, ErrorHandler]:
    """Setup logging and error handling for the simulation
    
    Returns:
        tuple: (logger, error_handler)
    """
    # Create logs directory if using file logging
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = SimulationLogger(
        name="simulation",
        log_level=log_level,
        log_file=log_file,
        enable_rich=enable_rich
    )
    
    # Create error handler
    error_handler = ErrorHandler(logger)
    
    # Register some common recovery strategies
    def api_error_recovery(error, context):
        """Recovery strategy for API errors"""
        if "rate limit" in str(error).lower():
            logger.info("Rate limit detected, waiting 5 seconds...")
            time.sleep(5)
            return True
        return False
    
    def connection_error_recovery(error, context):
        """Recovery strategy for connection errors"""
        logger.info("Connection error detected, retrying in 3 seconds...")
        time.sleep(3)
        return True
    
    # Register recovery strategies
    try:
        from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
        error_handler.register_recovery_strategy(ResourceExhausted, api_error_recovery)
        error_handler.register_recovery_strategy(GoogleAPICallError, connection_error_recovery)
    except ImportError:
        pass
    
    logger.info("Simulation logging system initialized")
    
    return logger, error_handler


# Global logger instance (can be imported and used across modules)
_global_logger = None
_global_error_handler = None


def get_logger() -> SimulationLogger:
    """Get the global logger instance"""
    global _global_logger, _global_error_handler
    
    if _global_logger is None:
        _global_logger, _global_error_handler = setup_simulation_logging()
    
    return _global_logger


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _global_logger, _global_error_handler
    
    if _global_error_handler is None:
        _global_logger, _global_error_handler = setup_simulation_logging()
    
    return _global_error_handler


if __name__ == "__main__":
    # Example usage
    logger, error_handler = setup_simulation_logging(
        log_level="DEBUG",
        log_file="logs/simulation.log"
    )
    
    # Test logging
    logger.info("Testing simulation logger")
    logger.debug("Debug message", component="test", step=1)
    logger.warning("Warning message", agent="TestAgent")
    
    # Test performance timing
    with logger.performance_timer("test_operation"):
        time.sleep(0.1)
    
    # Test error handling
    try:
        raise ValueError("Test error")
    except Exception as e:
        error_handler.handle_error(e, {"test": "context"})
    
    # Show performance summary
    logger.log_performance_summary()
    
    print("\n" + "="*50)
    print("Error Summary:")
    print(json.dumps(error_handler.get_error_summary(), indent=2))