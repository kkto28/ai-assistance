"""
File skill: read/write/list files in the agent's workspace.
Writes are dangerous (require approval); reads are not.
"""
import os
from pathlib import Path
from skills import tool

# All file operations are jailed to this directory so the agent can't
# wander the whole filesystem by default. Widen deliberately if needed.
WORKSPACE = Path(os.getenv("CLAWBOT_WORKSPACE", "./workspace")).resolve()
WORKSPACE.mkdir(exist_ok=True)


def _safe_path(path: str) -> Path:
    p = (WORKSPACE / path).resolve()
    if WORKSPACE not in p.parents and p != WORKSPACE:
        raise ValueError(f"Path '{path}' escapes the workspace sandbox.")
    return p


@tool(name="read_file", description="Read the contents of a file in the workspace.")
def read_file(path: str) -> str:
    try:
        return _safe_path(path).read_text()
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="write_file",
    description="Write text content to a file in the workspace (overwrites).",
    dangerous=True,
)
def write_file(path: str, content: str) -> str:
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error: {e}"


@tool(name="list_files", description="List files in a workspace directory.")
def list_files(path: str = ".") -> str:
    try:
        target = _safe_path(path)
        return "\n".join(sorted(p.name for p in target.iterdir())) or "(empty)"
    except Exception as e:
        return f"Error: {e}"
