import re
import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console

VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")


class VersionManager:
    """
    A class to manage version updates in a Python project.
    Handles updating version in pyproject.toml, committing changes, and creating git tags.
    """

    def __init__(self, project_root: Path, console: Optional[Console] = None):
        """
        Initialize the VersionManager.

        Args:
            project_root (str, optional): Path to the project root. Defaults to current directory.
            console (rich.console.Console, optional): Rich console for output. Creates a new one if None.
        """
        self._project_root = project_root
        self._pyproject_path = self._project_root / "pyproject.toml"
        self._con = console or Console()

        # Verify pyproject.toml exists
        if not self._pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {self._pyproject_path}")

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
            if not VERSION_PATTERN.search(content):
                self._con.print("[red]Error: Could not find version pattern in pyproject.toml")
                return False

            # Update the version in pyproject.toml
            new_content = VERSION_PATTERN.sub(f'version = "{version}"', content)

            # Write the updated content back to pyproject.toml
            self._pyproject_path.write_text(new_content)

            self._con.print(f"[green]Updated version to {version} in pyproject.toml")
            return True
        except Exception as e:
            self._con.print(f"[red]Error updating version: {str(e)}")
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

    def _commit_changes(self, version):
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
            ["git", "commit", "-m", f"Bump version to v{version}"], "Failed to commit changes"
        ):
            return False

        # Push the commit
        if not self._run_command(["git", "push"], "Failed to push changes"):
            return False

        self._con.print(f"[green]Committed and pushed changes for version {version}")
        return True

    def _create_git_tag(self, version):
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

    def run(self, version: str):
        """
        Run the complete version update process.

        Args:
            version (str): The new version number

        Returns:
            bool: True if all steps completed successfully
        """
        # Validate version format

        if not VERSION_PATTERN.match(version):
            self._con.print(
                f"[red]Invalid version format: {version}. Expected format: {{MAJOR}}.{{MINOR}}.{{PATCH}}"
            )
            return False

        steps = [
            (self._update_version, "Updating version in pyproject.toml"),
            (self._commit_changes, "Committing changes to git"),
            (self._create_git_tag, "Creating and pushing git tag"),
        ]

        for step_func, step_desc in steps:
            self._con.print(f"[blue]Step: {step_desc}...")
            if not step_func(version):
                self._con.print(f"[red]Failed at: {step_desc}")
                return False

        self._con.print(f"[green bold]✓ Version {version} successfully released!")
        return True
