import os
import shutil
import sys

import humanize
import psutil
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header

# The 'resource' module is POSIX-specific (Linux, macOS) and not available on Windows.
# We'll check for its availability and handle it gracefully.
try:
    import resource

    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False


def get_os_info() -> list[tuple]:
    """
    Gathers various OS and filesystem configurations.

    Returns:
        A list of tuples, where each tuple contains the configuration name,
        its value, and a description.
    """
    info = [("", "CPU", "")]

    # --- Section: CPU Information ---
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    info.append(
        ("CPU Physical Cores", str(physical_cores), "Number of physical CPU cores.")
    )
    info.append(
        (
            "CPU Logical Processors",
            str(logical_cores),
            "Total number of CPU threads (hyper-threading).",
        )
    )

    # --- Section: Memory Information ---
    info.append(("", "Memory Information", ""))  # Section header
    virtual_mem = psutil.virtual_memory()
    info.append(
        (
            "Total RAM",
            humanize.naturalsize(virtual_mem.total, binary=True),
            "Total physical memory (RAM).",
        )
    )
    info.append(
        (
            "Available RAM",
            humanize.naturalsize(virtual_mem.available, binary=True),
            "Memory available for new processes without swapping.",
        )
    )
    swap_mem = psutil.swap_memory()
    info.append(
        (
            "Total Swap",
            humanize.naturalsize(swap_mem.total, binary=True),
            "Total swap space available on disk.",
        )
    )

    # --- Section: Process Resource Limits (POSIX-specific) ---
    info.append(("", "Process Resource Limits", ""))  # Section header
    if RESOURCE_AVAILABLE:
        # Helper to format resource limits, which can be -1 for "unlimited"
        def format_limit(value, formatter=None):
            if value in [-1, resource.RLIM_INFINITY]:
                return "Unlimited"
            return formatter(value) if formatter else f"{value:,}"

        # Max Open Files per process
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        info.append(
            (
                "Max Open Files (Soft)",
                format_limit(soft),
                "The effective maximum number of open file descriptors per process.",
            )
        )
        info.append(
            (
                "Max Open Files (Hard)",
                format_limit(hard),
                "The absolute upper bound for the soft limit, set by the root user.",
            )
        )

        # Stack Size per process
        soft, hard = resource.getrlimit(resource.RLIMIT_STACK)
        info.append(
            (
                "Stack Size (Soft)",
                format_limit(soft, lambda v: humanize.naturalsize(v, binary=True)),
                "The effective maximum process stack size.",
            )
        )
        info.append(
            (
                "Stack Size (Hard)",
                format_limit(hard, lambda v: humanize.naturalsize(v, binary=True)),
                "The absolute upper bound for the stack size.",
            )
        )

        # Max Processes per user
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        info.append(
            (
                "Max Processes (Soft)",
                format_limit(soft),
                "The effective maximum number of processes a user can create.",
            )
        )

        # Virtual Memory (Address Space) Limit
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        info.append(
            (
                "Virtual Memory (Soft)",
                format_limit(soft, lambda v: humanize.naturalsize(v, binary=True)),
                "The effective max virtual memory (address space) a process can use.",
            )
        )

        # CPU Time Limit
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        info.append(
            (
                "CPU Time (Soft)",
                format_limit(soft, humanize.naturaldelta),
                "The max CPU time a process can consume before being sent a signal.",
            )
        )

    else:
        info.append(
            (
                "Resource Limits",
                "Not Available",
                "The 'resource' module is not available on this OS (e.g., Windows).",
            )
        )

    # --- Section: Filesystem Limits ---
    info.append(("", "Filesystem Limits", ""))  # Section header
    path = "/" if sys.platform != "win32" else "C:\\"
    try:
        max_filename = os.pathconf(path, "PC_NAME_MAX")
        info.append(
            (
                "Max Filename Length",
                f"{max_filename} characters",
                f"For the filesystem at '{path}'.",
            )
        )
    except (OSError, AttributeError):
        info.append(
            (
                "Max Filename Length",
                "Not Available",
                "Could not be determined for this filesystem.",
            )
        )

    try:
        max_path = os.pathconf(path, "PC_PATH_MAX")
        info.append(
            (
                "Max Path Length",
                f"{max_path} characters",
                f"For the filesystem at '{path}'.",
            )
        )
    except (OSError, AttributeError):
        info.append(
            (
                "Max Path Length",
                "Not Available",
                "Could not be determined for this filesystem.",
            )
        )

    # --- Section: Disk and Inode Information ---
    info.append(("", "Mounted Filesystems", ""))  # Section header
    processed_devices = set()
    for part in psutil.disk_partitions():
        if (
            "loop" in part.device
            or "squashfs" in part.fstype
            or not os.path.exists(part.mountpoint)
        ):
            continue
        if part.device in processed_devices:
            continue
        processed_devices.add(part.device)

        try:
            usage = shutil.disk_usage(part.mountpoint)
            info.append(
                (
                    f"Disk: {part.mountpoint}",
                    f"{humanize.naturalsize(usage.total)} Total, {humanize.naturalsize(usage.free)} Free",
                    f"Device: {part.device}",
                )
            )
        except OSError as e:
            info.append(
                (
                    f"Disk: {part.mountpoint}",
                    f"Error: {e.strerror}",
                    f"Device: {part.device}",
                )
            )

        if hasattr(os, "statvfs"):
            try:
                stats = os.statvfs(part.mountpoint)
                total_inodes = stats.f_files
                free_inodes = stats.f_ffree
                if total_inodes > 0:
                    info.append(
                        (
                            f"Inodes: {part.mountpoint}",
                            f"{humanize.intcomma(total_inodes)} Total, {humanize.intcomma(free_inodes)} Free",
                            f"Filesystem type: {part.fstype}",
                        )
                    )
            except OSError as e:
                info.append(
                    (
                        f"Inodes: {part.mountpoint}",
                        f"Error: {e.strerror}",
                        f"Filesystem type: {part.fstype}",
                    )
                )

    return info


class LimitsApp(App):
    """A Textual application to display OS configurations."""

    TITLE = "OS Limits Viewer"
    SUB_TITLE = "Displays key OS and filesystem limits"
    CSS_PATH = "limits.css"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container():
            yield DataTable(id="os_info_table")
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted to populate the table."""
        self.populate_table()

    def action_refresh(self) -> None:
        """Called when the user presses the 'r' key to refresh data."""
        self.populate_table()

    def populate_table(self) -> None:
        """Gathers data and populates the DataTable widget."""
        table = self.query_one(DataTable)
        table.clear()  # Clear previous data on refresh
        if not table.columns:
            table.add_columns("Configuration", "Value", "Description")
            table.cursor_type = "row"
            table.zebra_stripes = True

        os_info = get_os_info()
        for item in os_info:
            if item[1] in (
                "CPU",
                "Memory Information",  # <-- Add new section header
                "Process Resource Limits",
                "Filesystem Limits",
                "Mounted Filesystems",
            ):
                table.add_row()
            table.add_row(*item, label=item[0])


if __name__ == "__main__":
    app = LimitsApp()
    app.run()
