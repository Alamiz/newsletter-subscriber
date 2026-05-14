from __future__ import annotations

from pathlib import Path

from core.models import Status


class OutputManager:
    """
    Resolves and creates output directories.

    Final layout:
        output/<newsletter>/<STATUS>/<safe_email>/
            run.log
            metadata.json
            screenshots/
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_email_dir(
        self, newsletter: str, status: Status, email: str
    ) -> Path:
        safe = (
            email
            .replace("@", "_at_")
            .replace(".", "_dot_")
            .replace("+", "_plus_")
        )
        path = self.output_dir / newsletter / status.value / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_tmp_log(self, email: str, newsletter: str) -> Path:
        """Temporary log path used during execution before status is known."""
        safe_email = email.replace("@", "_at_").replace(".", "_dot_")
        tmp = self.output_dir / "_tmp" / f"{safe_email}__{newsletter}.log"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        return tmp
