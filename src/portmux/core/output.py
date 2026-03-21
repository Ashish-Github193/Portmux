"""Centralized output channel for PortMUX."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class Output:
    """Centralized output channel for all PortMUX output.

    All modules use this instead of creating their own Console().
    Enables future TUI mode, --json mode, --quiet mode, and log redirection
    by swapping or configuring a single instance.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def success(self, msg: str) -> None:
        self.console.print(f"[green]{msg}[/green]")

    def error(self, msg: str) -> None:
        self.console.print(f"[red]{msg}[/red]")

    def warning(self, msg: str) -> None:
        self.console.print(f"[yellow]{msg}[/yellow]")

    def info(self, msg: str) -> None:
        self.console.print(f"[blue]{msg}[/blue]")

    def verbose(self, msg: str, is_verbose: bool) -> None:
        if is_verbose:
            self.console.print(f"[blue]{msg}[/blue]")

    def dim(self, msg: str) -> None:
        self.console.print(f"[dim]{msg}[/dim]")

    def print(self, *args, **kwargs) -> None:
        """Pass-through to console.print for complex formatting."""
        self.console.print(*args, **kwargs)

    def table(self, table: Table) -> None:
        self.console.print(table)

    def panel(self, content: str, **kwargs) -> None:
        self.console.print(Panel(content, **kwargs))

    @contextmanager
    def progress_context(self) -> Generator[ProgressReporter, None, None]:
        """Context manager for progress reporting with a spinner."""
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            yield ProgressReporter(progress)


class ProgressReporter:
    """Wraps Rich Progress to provide a simple update/finish API."""

    def __init__(self, progress):
        self._progress = progress
        self._current_task = None

    def update(self, description: str) -> None:
        """Start or replace the current progress task."""
        if self._current_task is not None:
            self._progress.remove_task(self._current_task)
        self._current_task = self._progress.add_task(description, total=None)

    def finish(self) -> None:
        """Remove the current progress task."""
        if self._current_task is not None:
            self._progress.remove_task(self._current_task)
            self._current_task = None
