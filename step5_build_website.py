"""Step 5: build the project website (docs/index.html) from your real results.

Run step 3 first. In PyCharm: open this file and click the green ▶ arrow below.
Then in Finder open GasStorage → docs and double-click index.html to preview it.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

if __name__ == "__main__":
    if not PY.exists():
        sys.exit("!! Run step1_setup.py first.")
    code = "from gasstore import website; print('Built', website.build())"
    sys.exit(subprocess.call([str(PY), "-c", code], cwd=HERE))
