from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .step import Step


@dataclass
class StepResult:
    """
    Class to represent the result of a step execution.

    Attributes:
        step: The step that was executed
        success: Whether the step execution was successful
        message: A message describing the result
        exception: Any exception that occurred during execution
        details: Additional details about the step execution
    """

    step: Step
    success: bool
    message: str = ""
    exception: Optional[Exception] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow boolean evaluation of the result based on success."""
        return self.success
