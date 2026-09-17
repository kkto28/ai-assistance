"""
Shell skill: lets the agent run local shell commands.
Marked dangerous=True so it goes through the approval gate unless
auto_approve is enabled in config.
"""
import subprocess
from skills import tool


@tool(
    name="run_shell",
    description="Run a shell command on the local machine and return stdout/stderr.",
    dangerous=True,
)
def run_shell(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr.strip()}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30s"
    except Exception as e:
        return f"Error: {e}"
