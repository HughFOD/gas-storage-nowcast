"""Step 4: run the automatic checks (no future data leaks into any forecast,
the pipeline works end to end). About 15 seconds.

In PyCharm: open this file and click the green ▶ arrow below.
"""
import sys

from launch import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "test"]
    main()
