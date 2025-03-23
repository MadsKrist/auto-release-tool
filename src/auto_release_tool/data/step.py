from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Step:
    """
    Represents a step in a process with an optional rollback function.

    Attributes:
        func (Callable): The main function to execute for this step.
        description (str): A description of the step.
        rollback_func (Optional[Callable]): An optional function to rollback this step.
    """

    func: Callable
    description: str
    rollback_func: Optional[Callable] = None
