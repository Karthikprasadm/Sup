import json
import subprocess
import sys
from pathlib import Path

examples_dir = Path("sup-lang/examples")
results = []


def run(cmd, input_text=None, timeout=10):
    return subprocess.run(
        cmd, input=input_text, capture_output=True, text=True, timeout=timeout
    )


for sup_file in sorted(examples_dir.glob("*.sup")):
    cmd = [sys.executable, "-u", "-m", "sup.cli", str(sup_file)]

    # Special handling
    if sup_file.name == "05_input.sup":
        p = run(cmd, input_text="hello\n")
    else:
        # Ensure todo store is clean for 15_todo
        if sup_file.name == "15_todo.sup":
            store = Path("todos.json")
            if store.exists():
                try:
                    store.unlink()
                except Exception:
                    pass
        p = run(cmd)

    entry = {
        "file": str(sup_file),
        "returncode": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }

    # Treat the intentional throw as OK
    if sup_file.name == "11_errors.sup" and ("boom" in entry["stderr"]):
        entry["returncode"] = 0

    results.append(entry)

summary = {
    "ok": [r["file"] for r in results if r["returncode"] == 0],
    "fail": [
        {k: r[k] for k in ["file", "returncode", "stdout", "stderr"]}
        for r in results
        if r["returncode"] != 0
    ],
}
print(json.dumps(summary, indent=2))
