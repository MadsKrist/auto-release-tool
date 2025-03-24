from pathlib import Path
from typing import List, Optional
from .process_manager import ProcessManager
from auto_release_tool.data import Step, StepResult

from rich.console import Console


class ErrorManager(ProcessManager):

    def __init__(self, project_root: Path, console: Optional[Console]):
        super().__init__(console)

    def _get_steps(self) -> List[Step]:

        return [
            Step(func=self._run_sourcery, description="Running sourcery", rollback_func=None),
            Step(func=self._run_pytest, description="Running pytest", rollback_func=None),
        ]

    def _run_sourcery(self) -> None:
        raise NotImplementedError

    def _run_pytest(self) -> None:
        raise NotImplementedError

    def _validate_input(self, *args, **kwargs) -> StepResult:
        raise NotImplementedError
