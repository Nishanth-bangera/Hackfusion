from app.tools.db_tools import find_alternatives

for product_id in (1, 2, 3):
    print(product_id, find_alternatives(product_id, "Shanghai"))
