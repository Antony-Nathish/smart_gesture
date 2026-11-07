"""Launch the integrated Gesture-Cursor dashboard."""
import subprocess
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
SUPPORTED_PYTHON = (3, 9) <= sys.version_info[:2] < (3, 13)

if not SUPPORTED_PYTHON:
    venv_python = APP_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        version = subprocess.run(
            [
                str(venv_python),
                "-c",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if version.returncode == 0 and version.stdout.strip() == "3.12":
            raise SystemExit(
                subprocess.run(
                    [str(venv_python), str(Path(__file__).resolve())],
                    cwd=APP_DIR,
                    check=False,
                ).returncode
            )

    raise SystemExit(
        "Gesture-Cursor requires Python 3.9-3.12 (Python 3.12 recommended). "
        "Run run.bat to create the compatible .venv and install dependencies, "
        "then run main.py again."
    )

def main():
    from control_dashboard import GestureDashboard

    GestureDashboard().mainloop()


if __name__ == "__main__":
    main()
