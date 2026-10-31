"""Step 3: download real EIA storage data (2010 to now) and weather for 17
cities, then test the models and make this week's nowcast.

In PyCharm: open this file and click the green ▶ arrow next to
`if __name__ == "__main__":` below. The first run downloads 26 years of
weather and takes a few minutes; after that it only fetches new weeks.
Results appear in output/real. Run it again each week for a fresh nowcast.
"""
import sys

from launch import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "analyze"]
    main()
