from app.schemas import Exposure, ImpactReport, SentinelVerdict
from app.tools.db_tools import find_exposures


def run_impact(verdict: SentinelVerdict) -> ImpactReport:
    """Turn a confirmed disruption into a ranked list of exposed orders."""
    if not verdict.confirmed or verdict.confidence < 0.5:
        # Weak evidence is escalated by the orchestrator, not analyzed autonomously.
        return ImpactReport(
            exposed=False,
            total_orders_at_risk=0,
            worst_stockout_days=0,
            exposures=[],
        )

    rows = find_exposures(verdict.location, verdict.delay_days)
    exposures = [Exposure(**{key: row[key] for key in Exposure.model_fields}) for row in rows]
    worst = max((exposure.stockout_days for exposure in exposures), default=0)
    return ImpactReport(
        exposed=bool(exposures),
        total_orders_at_risk=len(exposures),
        worst_stockout_days=worst,
        exposures=exposures,
    )
