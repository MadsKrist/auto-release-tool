from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt
from typer import Option
from typing_extensions import Annotated

from auto_release_tool import VersionManager, ErrorManager

app = typer.Typer()
con = Console()


def validate_folder() -> bool:

    root = Path.cwd()

    if not (root / ".git").exists():
        con.print("[red]Error: This is not a git repository")
        return False

    return True


@app.command()
def init():

    if not validate_folder():
        raise typer.Exit()

    project_name = Prompt.ask("Enter the project name")
    project_type = Prompt.ask("Project type", choices=["FastAPI", "Jinja2"])
    project_description = Prompt.ask("Enter the project description")


@app.command()
def publish(
    version: Annotated[
        str, Option(help="Version number with the format: '{MAJOR}.{MINOR}.{PATCH}'")
    ],
    project_root: Annotated[str, Option(help="Path to the project")] = "",
):
    root = Path(project_root)

    if not project_root:
        root = Path.cwd()

    try:
        manager = VersionManager(root, console=con)
    except FileNotFoundError as e:
        con.print(f"[red]Error: {str(e)}")
        raise typer.Exit()

    manager.run(version)


@app.command()
def error_check(
    project_root: Annotated[str, Option(help="Path to the project")] = "",
):
    root = Path(project_root)

    if not project_root:
        root = Path.cwd()

    try:
        manager = ErrorManager(root, console=con)
    except FileNotFoundError as e:
        con.print(f"[red]Error: {str(e)}")
        raise typer.Exit()


@app.command()
def delete():
    con.print("Deleting version")


if __name__ == "__main__":
    app()
