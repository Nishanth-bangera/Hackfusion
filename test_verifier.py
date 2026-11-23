"""
test_verifier.py — tests the Verifier agent against procurement policies.

Expected outcomes:
  Chennai (lead=3d, price=128): APPROVED   (3<=14, 128 <= 118*1.20=141.6)
  Hanoi late (lead=15d):        REJECTED   (15 > max_lead_time_days 14)
  Big order (needed=15000):     ESCALATE   (15000 > max_order_units 10000)
"""
from app.agents.verifier import check_candidate

# Test 1: Chennai candidate — should be APPROVED
chennai = {
    "supplier_name": "Chennai Components Pvt (MOCK)",
    "port": "Chennai",
    "unit_price_inr": 128.0,
    "lead_time_days": 3,
    "capacity_units": 20000,
}
r1 = check_candidate(
    chennai,
    current_unit_price=118.0,
    stockout_days=4,
    needed_units=6000,
    confidence=0.86,
)
print(f"Chennai:    {r1['decision']} — {r1['reason']}")
assert r1["decision"] == "APPROVED", f"Expected APPROVED, got {r1}"

# Test 2: Hanoi-style supplier with long lead time — should be REJECTED (lead 15 > 14)
hanoi_late = {
    "supplier_name": "Hanoi Parts Co late-variant (MOCK)",
    "port": "Haiphong",
    "unit_price_inr": 122.0,
    "lead_time_days": 15,   # exceeds max_lead_time_days=14
    "capacity_units": 30000,
}
r2 = check_candidate(
    hanoi_late,
    current_unit_price=118.0,
    stockout_days=10,
    needed_units=6000,
    confidence=0.86,
)
print(f"Hanoi late: {r2['decision']} — {r2['reason']}")
assert r2["decision"] == "REJECTED", f"Expected REJECTED, got {r2}"

# Test 3: Large order — should ESCALATE (15000 > max_order_units 10000)
big = {
    "supplier_name": "Chennai Components Pvt (MOCK)",
    "port": "Chennai",
    "unit_price_inr": 128.0,
    "lead_time_days": 3,
    "capacity_units": 50000,
}
r3 = check_candidate(
    big,
    current_unit_price=118.0,
    stockout_days=4,
    needed_units=15000,
    confidence=0.86,
)
print(f"Big order:  {r3['decision']} — {r3['reason']}")
assert r3["decision"] == "ESCALATE", f"Expected ESCALATE, got {r3}"

print("\nAll verifier tests passed.")
