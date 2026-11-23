from datetime import date

from app.tools.db_tools import find_exposures

for exposure in find_exposures("Shanghai", delay_days=5, today=date(2026, 11, 23)):
    print(exposure)
