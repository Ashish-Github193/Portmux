"""Service layer for PortMUX — coordinates operations between modules."""

from __future__ import annotations

import time

from ..backend import TmuxBackend, TunnelBackend
from ..models import ForwardInfo, PortmuxConfig
from ..ssh.forwards import (
    add_forward as _add_forward,
)
from ..ssh.forwards import (
    list_forwards as _list_forwards,
)
from ..ssh.forwards import (
    refresh_forward as _refresh_forward,
)
from ..ssh.forwards import (
    remove_forward as _remove_forward,
)
from .config import (
    get_default_identity,
)
from .output import Output
from .profiles import list_available_profiles, load_profile, profile_exists
from .startup import execute_startup_commands, startup_commands_enabled


class PortmuxService:
    """Coordinates operations between config, session, forwards, startup.

    Commands become thin Click wrappers that parse args and call the service.
    New features (health checks, hooks, event logging) get added here.
    """

    def __init__(
        self,
        config: PortmuxConfig,
        output: Output,
        session_name: str | None = None,
        backend: TunnelBackend | None = None,
    ):
        self.config = config
        self.output = output
        self.session_name = session_name or config.session_name
        self.backend = backend or TmuxBackend()

    def initialize(
        self,
        profile: str | None = None,
        force: bool = False,
        run_startup: bool = True,
        verbose: bool = False,
    ) -> bool:
        """Initialize a PortMUX session.

        Args:
            profile: Profile name to load (optional)
            force: Force recreation of existing session
            run_startup: Whether to run startup commands
            verbose: Enable verbose output

        Returns:
            True if initialization succeeded
        """
        # Handle profile loading
        if profile:
            self.output.verbose(f"Loading profile '{profile}'...", verbose)

            if not profile_exists(self.config, profile):
                available = list_available_profiles(self.config)
                self.output.error(f"Profile '{profile}' not found")
                if available:
                    self.output.info(f"Available profiles: {', '.join(available)}")
                else:
                    self.output.info("No profiles are configured")
                return False

            self.config = load_profile(profile, self.config)
            self.session_name = self.config.session_name
            self.output.success(f"Profile '{profile}' loaded")

        # Check if session exists
        if self.backend.session_exists(self.session_name):
            if force:
                self.output.warning(
                    f"Destroying existing session '{self.session_name}'..."
                )
                self.backend.kill_session(self.session_name)
            else:
                self.output.warning(f"Session '{self.session_name}' already exists")
                self.output.print("Use --force to recreate the session")
                return True  # Not an error, just already exists

        # Create session
        self.output.verbose(f"Creating tmux session '{self.session_name}'...", verbose)

        success = self.backend.create_session(self.session_name)
        if success:
            self.output.success(
                f"Successfully initialized PortMUX session '{self.session_name}'"
            )

            if profile:
                self.output.info(f"Initialized with profile: {profile}")

            # Execute startup commands if enabled and not skipped
            if run_startup and startup_commands_enabled(self.config):
                self.output.verbose("Executing startup commands...", verbose)
                startup_success = execute_startup_commands(
                    self.config, self.session_name, verbose, self.output
                )
                if startup_success:
                    self.output.success("Startup commands completed successfully")
                else:
                    self.output.warning(
                        "Some startup commands failed (session still active)"
                    )
            elif not run_startup:
                self.output.verbose("Startup commands skipped (--no-startup)", verbose)
            elif verbose:
                self.output.verbose("No startup commands configured", verbose)

            self.output.info("Use 'portmux status' to view session details")
        else:
            self.output.warning(f"Session '{self.session_name}' already exists")

        return True

    def add_forward(
        self,
        direction: str,
        spec: str,
        host: str,
        identity: str | None = None,
        verbose: bool = False,
    ) -> str:
        """Add a new SSH port forward.

        Args:
            direction: "L" for local, "R" for remote
            spec: Port specification like "8080:localhost:80"
            host: SSH target like "user@hostname"
            identity: Path to SSH key file (optional)
            verbose: Enable verbose output

        Returns:
            Window name created
        """
        # Resolve identity
        if not identity:
            identity = self.config.default_identity or get_default_identity()
            if verbose and identity:
                self.output.info(f"Using default identity: {identity}")

        # Initialize session if needed
        self._init_session_if_needed()

        # Create the forward
        if verbose:
            direction_name = "Local" if direction == "L" else "Remote"
            self.output.info(
                f"Creating {direction_name.lower()} forward {spec} to {host}..."
            )

        window_name = _add_forward(
            direction=direction,
            spec=spec,
            host=host,
            identity=identity,
            session_name=self.session_name,
            backend=self.backend,
        )

        direction_name = "Local" if direction == "L" else "Remote"
        self.output.success(
            f"Successfully created {direction_name.lower()} forward '{window_name}'"
        )

        return window_name

    def remove_forward(self, name: str, verbose: bool = False) -> bool:
        """Remove a single forward by name.

        Args:
            name: Forward name (e.g., "L:8080:localhost:80")
            verbose: Enable verbose output

        Returns:
            True if removed
        """
        self.output.verbose(f"Removing forward '{name}'...", verbose)
        _remove_forward(name, self.session_name, backend=self.backend)
        self.output.success(f"Successfully removed forward '{name}'")
        return True

    def remove_all_forwards(self, verbose: bool = False) -> int:
        """Remove all forwards.

        Args:
            verbose: Enable verbose output

        Returns:
            Number of forwards removed
        """
        forwards = self.list_forwards()
        if not forwards:
            self.output.warning(
                f"No forwards to remove in session '{self.session_name}'"
            )
            return 0

        removed_count = 0
        for forward in forwards:
            try:
                _remove_forward(forward.name, self.session_name, backend=self.backend)
                removed_count += 1
                if verbose:
                    self.output.success(f"Removed forward '{forward.name}'")
            except Exception as e:
                self.output.error(f"Failed to remove '{forward.name}': {e}")

        self.output.success(f"Successfully removed {removed_count} forward(s)")
        return removed_count

    def destroy_session(self, verbose: bool = False) -> bool:
        """Destroy the entire session.

        Args:
            verbose: Enable verbose output

        Returns:
            True if destroyed
        """
        self.output.verbose(f"Destroying session '{self.session_name}'...", verbose)
        self.backend.kill_session(self.session_name)
        self.output.success(f"Session '{self.session_name}' destroyed successfully")
        return True

    def list_forwards(self) -> list[ForwardInfo]:
        """List all active forwards.

        Returns:
            List of ForwardInfo objects
        """
        return _list_forwards(self.session_name, backend=self.backend)

    def refresh_forward(self, name: str, verbose: bool = False) -> bool:
        """Refresh a single forward.

        Args:
            name: Forward name
            verbose: Enable verbose output

        Returns:
            True if refreshed
        """
        _refresh_forward(name, self.session_name, backend=self.backend)
        if verbose:
            self.output.success(f"Refreshed forward '{name}'")
        return True

    def refresh_all(
        self,
        delay: float | None = None,
        reload_startup: bool = False,
        verbose: bool = False,
    ) -> int:
        """Refresh all forwards.

        Args:
            delay: Delay between refreshes in seconds
            reload_startup: Whether to re-execute startup commands after refresh
            verbose: Enable verbose output

        Returns:
            Number of forwards refreshed
        """
        if delay is None:
            delay = self.config.reconnect_delay

        forwards = self.list_forwards()
        if not forwards:
            self.output.warning(
                f"No forwards to refresh in session '{self.session_name}'"
            )
            return 0

        self.output.info(
            f"Refreshing all {len(forwards)} forward(s) with {delay}s delay..."
        )

        refreshed_count = 0
        with self.output.progress_context() as progress:
            for i, forward in enumerate(forwards):
                progress.update(f"Refreshing {forward.name} ({i + 1}/{len(forwards)})")

                try:
                    _refresh_forward(
                        forward.name, self.session_name, backend=self.backend
                    )
                    refreshed_count += 1
                    if verbose:
                        self.output.success(f"Refreshed forward '{forward.name}'")

                    # Add delay between refreshes (except for last one)
                    if i < len(forwards) - 1 and delay > 0:
                        time.sleep(delay)

                except Exception as e:
                    self.output.error(f"Failed to refresh '{forward.name}': {e}")

                progress.finish()

        self.output.success(
            f"Successfully refreshed {refreshed_count}/{len(forwards)} forward(s)"
        )

        # Handle startup reload
        if reload_startup:
            self.handle_startup_reload(verbose)

        return refreshed_count

    def get_status(self) -> dict:
        """Get session status information.

        Returns:
            Dict with session_active and forwards
        """
        active = self.backend.session_exists(self.session_name)
        forwards = (
            _list_forwards(self.session_name, backend=self.backend) if active else []
        )
        return {
            "session_name": self.session_name,
            "session_active": active,
            "forwards": forwards,
        }

    def session_is_active(self) -> bool:
        """Check if the tmux session is active."""
        return self.backend.session_exists(self.session_name)

    def _init_session_if_needed(self) -> None:
        """Create session if it doesn't exist."""
        if not self.backend.session_exists(self.session_name):
            self.output.warning(f"Initializing session '{self.session_name}'...")
            self.backend.create_session(self.session_name)
            self.output.success(f"Session '{self.session_name}' created successfully")

    async def check_health(self) -> list:
        """Run on-demand health check on all forwards.

        Returns:
            List of HealthResult objects
        """
        from ..health import HealthChecker

        checker = HealthChecker(
            self.backend,
            self.session_name,
            tcp_timeout=self.config.monitor.tcp_timeout,
        )
        forwards = self.list_forwards()
        return await checker.check_all(forwards)

    def create_monitor(self):
        """Create a TunnelMonitor for continuous health watching.

        Returns:
            TunnelMonitor instance
        """
        from ..health import TunnelMonitor

        return TunnelMonitor(
            backend=self.backend,
            config=self.config,
            output=self.output,
            session_name=self.session_name,
        )

    def handle_startup_reload(self, verbose: bool) -> None:
        """Handle startup command reload after refresh."""
        if startup_commands_enabled(self.config):
            self.output.verbose("Re-executing startup commands...", verbose)
            success = execute_startup_commands(
                self.config, self.session_name, verbose, self.output
            )
            if success:
                self.output.success("Startup commands executed successfully")
            else:
                self.output.warning("Some startup commands failed")
        elif verbose:
            self.output.verbose("No startup commands configured for reload", verbose)
