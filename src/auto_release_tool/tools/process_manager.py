from typing import List, Optional, Dict, Any, Sequence
from rich.console import Console
from dataclasses import dataclass

from auto_release_tool.data import Step, StepResult


class ProcessManager:
    """
    A base class for managing multi-step processes.
    Provides a framework for defining, executing, and logging process steps
    with enhanced typing and rollback capabilities.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the ProcessManager.

        Args:
            console (rich.console.Console, optional): Rich console for output. Creates a new one if None.
        """
        self._con = console or Console()
        self._results: List[StepResult] = []

    def _get_steps(self) -> List[Step]:
        """
        Define the steps to be executed in the process.
        Override this method in subclasses to define specific steps.

        Returns:
            List[Step]: List of Step objects defining the process
        """
        return []

    def _validate_input(self, *args, **kwargs) -> StepResult:
        """
        Validate inputs before running the process.
        Override this method in subclasses to implement specific validation logic.

        Returns:
            StepResult: Result of the validation step
        """
        # Create a dummy Step for validation
        validation_step = Step(func=lambda *args, **kwargs: True, description="Input validation")

        return StepResult(step=validation_step, success=True, message="Input validation passed")

    def _execute_step(self, step: Step, *args, **kwargs) -> StepResult:
        """
        Execute a single step and return its result.

        Args:
            step (Step): The step to execute
            *args, **kwargs: Arguments to pass to the step function

        Returns:
            StepResult: Result of the step execution
        """
        self._con.print(f"[blue]Step: {step.description}...")

        try:
            success = step.func(*args, **kwargs)
            message = f"Step '{step.description}' {'succeeded' if success else 'failed'}"

            if success:
                self._con.print(f"[green]✓ {step.description} successful")
            else:
                self._con.print(f"[red]✗ {step.description} failed")

            return StepResult(step=step, success=bool(success), message=message)

        except Exception as e:
            error_message = f"Error in step '{step.description}': {str(e)}"
            self._con.print(f"[red]{error_message}")

            return StepResult(step=step, success=False, message=error_message, exception=e)

    def _rollback(self, executed_steps: List[StepResult], *args, **kwargs) -> None:
        """
        Rollback steps that have been executed in reverse order.

        Args:
            executed_steps (List[StepResult]): Steps that were successfully executed
            *args, **kwargs: Arguments to pass to rollback functions
        """
        self._con.print("[yellow]Rolling back previous steps...")

        # Iterate through completed steps in reverse order
        for result in reversed(executed_steps):
            step = result.step

            if step.rollback_func is not None:
                self._con.print(f"[yellow]Rolling back: {step.description}...")

                try:
                    success = step.rollback_func(*args, **kwargs)
                    status = "successful" if success else "failed"
                    self._con.print(f"[{'green' if success else 'red'}]Rollback {status}")
                except Exception as e:
                    self._con.print(f"[red]Error during rollback of '{step.description}': {str(e)}")

        self._con.print("[yellow]Rollback completed")

    def run(self, *args, **kwargs) -> bool:
        """
        Run the complete process by executing all steps in sequence.

        Returns:
            bool: True if all steps completed successfully, False otherwise
        """
        self._results = []
        successful_steps = []

        # Validate inputs
        validation_result = self._validate_input(*args, **kwargs)
        self._results.append(validation_result)

        if not validation_result.success:
            self._con.print(f"[red]Validation failed: {validation_result.message}")
            return False

        # Get the steps to execute
        steps = self._get_steps()

        # Execute each step
        for step in steps:
            result = self._execute_step(step, *args, **kwargs)
            self._results.append(result)

            if result.success:
                successful_steps.append(result)
            else:
                # If a step fails and we have rollback functions, trigger rollback
                if any(s.step.rollback_func is not None for s in successful_steps):
                    self._rollback(successful_steps, *args, **kwargs)
                return False

        self._con.print(f"[green bold]✓ Process completed successfully!")
        return True

    @property
    def results(self) -> List[StepResult]:
        """
        Get the results of the last process run.

        Returns:
            List[StepResult]: Results of executed steps
        """
        return self._results
