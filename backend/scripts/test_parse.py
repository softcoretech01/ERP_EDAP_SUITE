import sqlglot
from sqlglot.expressions import Table

sql = """SELECT COUNT(*) AS total_purchase_orders
FROM tbl_purchaseorder_header
WHERE MONTH(createddt) = MONTH(CURDATE())
  AND YEAR(createddt) = YEAR(CURDATE())"""

parsed = sqlglot.parse_one(sql, read="mysql")
query_tables = [t.name.lower() for t in parsed.find_all(Table)]
print(query_tables)
