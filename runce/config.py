from pathlib import Path
from tempfile import gettempdir


class Config:
    """Manage Runce configuration and data storage."""

    def __init__(self):
        self._data_dir = Path(gettempdir()) / "runce.v1"

    @property
    def data_dir(self) -> Path:
        """Get directory for run files."""
        return self._data_dir

    def ensure_data_dir(self) -> None:
        """Create data directory if missing."""
        self._data_dir.mkdir(parents=True, exist_ok=True)
