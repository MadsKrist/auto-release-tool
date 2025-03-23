from pathlib import Path

import typer
from rich.console import Console
from typer import Option
from typing_extensions import Annotated

from auto_release_tool import VersionManager

app = typer.Typer()
con = Console()


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
def delete():
    con.print("Deleting version")


if __name__ == "__main__":
    app()
