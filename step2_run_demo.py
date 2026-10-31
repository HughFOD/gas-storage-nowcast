"""Step 2: run the whole project on made-up data (no internet). About 20 seconds.

In PyCharm: open this file and click the green ▶ arrow next to
`if __name__ == "__main__":` below. Results appear in output/demo.
"""
import sys

from launch import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "demo"]
    main()
