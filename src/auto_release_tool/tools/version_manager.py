import re
import subprocess
from pathlib import Path
from typing import Optional, List
from rich.console import Console

from .process_manager import ProcessManager
from auto_release_tool.data import Step, StepResult

PYPROJECT_VERSION_PATTERN = re.compile(r'version = "\d+\.\d+\.\d+"')
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class VersionManager(ProcessManager):
    """
    A class to manage version updates in a Python project.
    Handles updating version in pyproject.toml, committing changes, and creating git tags.
    Now with rollback capabilities.
    """

    def __init__(self, project_root: Path, console: Optional[Console] = None):
        """
        Initialize the VersionManager.

        Args:
            project_root (Path): Path to the project root.
            console (rich.console.Console, optional): Rich console for output. Creates a new one if None.
        """
        super().__init__(console)
        self._project_root = project_root
        self._pyproject_path = self._project_root / "pyproject.toml"
        self._original_version = None  # To store for rollback

        # Verify pyproject.toml exists
        if not self._pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {self._pyproject_path}")

        # Store the original version when initializing
        try:
            content = self._pyproject_path.read_text()
            match = PYPROJECT_VERSION_PATTERN.search(content)
            if match:
                version_line = match.group(0)
                self._original_version = version_line.split('"')[1]
        except Exception:
            # If we can't get the original version, we'll proceed without rollback capability
            pass

    def _validate_input(self, version: str, *args, **kwargs) -> StepResult:
        """
        Validate the version format.

        Args:
            version (str): The version to validate

        Returns:
            StepResult: Result of the validation
        """
        validation_step = Step(
            func=lambda v: bool(VERSION_PATTERN.match(v)), description="Version format validation"
        )

        success = bool(VERSION_PATTERN.match(version))
        message = (
            f"Version {version} is valid"
            if success
            else f"Invalid version format: {version}. Expected format: {{MAJOR}}.{{MINOR}}.{{PATCH}}"
        )

        if not success:
            self._con.print(f"[red]{message}")

        return StepResult(step=validation_step, success=success, message=message)

    def _get_steps(self) -> List[Step]:
        """
        Define the steps for the version update process.

        Returns:
            List[Step]: List of Step objects
        """
        return [
            Step(
                func=self._update_version,
                description="Updating version in pyproject.toml",
                rollback_func=self._rollback_version_update,
            ),
            Step(
                func=self._commit_changes,
                description="Committing changes to git",
                rollback_func=self._rollback_commit,
            ),
            Step(
                func=self._create_git_tag,
                description="Creating and pushing git tag",
                rollback_func=self._rollback_git_tag,
            ),
        ]

    def _update_version(self, version: str) -> bool:
        """
        Update the version in pyproject.toml.

        Args:
            version (str): The new version number (e.g., "1.2.3")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read the pyproject.toml file
            content = self._pyproject_path.read_text()

            # Check if the version pattern exists
            if not PYPROJECT_VERSION_PATTERN.search(content):
                self._con.print("[red]Error: Could not find version pattern in pyproject.toml")
                return False

            # Update the version in pyproject.toml
            new_content = PYPROJECT_VERSION_PATTERN.sub(f'version = "{version}"', content)

            # Write the updated content back to pyproject.toml
            self._pyproject_path.write_text(new_content)

            self._con.print(f"[green]Updated version to {version} in pyproject.toml")
            return True
        except Exception as e:
            self._con.print(f"[red]Error updating version: {str(e)}")
            return False

    def _rollback_version_update(self, version: str) -> bool:
        """
        Rollback version update in pyproject.toml.

        Args:
            version (str): The version that was being set (not used directly)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._original_version:
            self._con.print("[yellow]No original version stored, cannot rollback")
            return False

        try:
            # Read the current content
            content = self._pyproject_path.read_text()

            # Replace with original version
            rollback_content = PYPROJECT_VERSION_PATTERN.sub(
                f'version = "{self._original_version}"', content
            )

            # Write the original content back
            self._pyproject_path.write_text(rollback_content)

            self._con.print(
                f"[green]Rolled back version to {self._original_version} in pyproject.toml"
            )
            return True
        except Exception as e:
            self._con.print(f"[red]Error rolling back version: {str(e)}")
            return False

    def _run_command(self, command, error_message):
        """
        Run a shell command and handle errors.

        Args:
            command (list): Command to run
            error_message (str): Error message to display if command fails

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True, cwd=self._project_root
            )
            return True

        except subprocess.CalledProcessError as e:
            self._con.print(f"[red]{error_message}")
            self._con.print(f"[red]Command: {' '.join(command)}")
            self._con.print(f"[red]Error: {e.stderr}")
            return False

        except Exception as e:
            self._con.print(f"[red]{error_message}: {str(e)}")
            return False

    def _commit_changes(self, version: str) -> bool:
        """
        Commit the version changes to git.

        Args:
            version (str): The version being committed

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if we're in a git repository
        if not self._run_command(
            ["git", "rev-parse", "--is-inside-work-tree"],
            "Not a git repository. Cannot commit changes.",
        ):
            return False

        # Add pyproject.toml to staging
        if not self._run_command(
            ["git", "add", "pyproject.toml"], "Failed to stage pyproject.toml"
        ):
            return False

        # Commit the changes
        if not self._run_command(
            ["git", "commit", "-m", f"Updated version to v{version}"], "Failed to commit changes"
        ):
            return False

        # Push the commit
        if not self._run_command(["git", "push"], "Failed to push changes"):
            return False

        self._con.print(f"[green]Committed and pushed changes for version {version}")
        return True

    def _rollback_commit(self, version: str) -> bool:
        """
        Rollback the git commit.

        Args:
            version (str): The version that was being committed

        Returns:
            bool: True if successful, False otherwise
        """
        # Reset the last commit
        if not self._run_command(
            ["git", "reset", "--hard", "HEAD~1"], "Failed to reset last commit"
        ):
            return False

        # Force push to remote (if necessary)
        if not self._run_command(["git", "push", "--force"], "Failed to force push rollback"):
            return False

        self._con.print(f"[green]Rolled back commit for version {version}")
        return True

    def _create_git_tag(self, version: str) -> bool:
        """
        Create and push a git tag for the version.

        Args:
            version (str): The version to tag

        Returns:
            bool: True if successful, False otherwise
        """
        # Create a new Git tag
        tag_command = ["git", "tag", "-a", f"v{version}", "-m", f"Release version {version}"]
        self._con.print(f"[green]Running: {' '.join(tag_command)}")

        if not self._run_command(tag_command, "Failed to create git tag"):
            return False

        # Push the tag
        push_command = ["git", "push", "origin", f"v{version}"]
        self._con.print(f"[green]Running: {' '.join(push_command)}")

        if not self._run_command(push_command, "Failed to push git tag"):
            return False

        self._con.print(f"[green]Successfully created and pushed tag v{version}")
        return True

    def _rollback_git_tag(self, version: str) -> bool:
        """
        Remove the git tag.

        Args:
            version (str): The version tag to remove

        Returns:
            bool: True if successful, False otherwise
        """
        # Delete the local tag
        if not self._run_command(
            ["git", "tag", "-d", f"v{version}"], f"Failed to delete local tag v{version}"
        ):
            return False

        # Delete the remote tag
        if not self._run_command(
            ["git", "push", "--delete", "origin", f"v{version}"],
            f"Failed to delete remote tag v{version}",
        ):
            return False

        self._con.print(f"[green]Successfully removed tag v{version}")
        return True

    def run(self, version: str) -> bool:
        """
        Run the complete version update process.

        Args:
            version (str): The new version number

        Returns:
            bool: True if all steps completed successfully
        """
        result = super().run(version)

        if result:
            self._con.print(f"[green bold]✓ Version {version} successfully released!")

        return result
