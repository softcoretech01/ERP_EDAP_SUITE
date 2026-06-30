import sqlglot

sql = """SELECT COUNT(*) AS PurchaseOrderCount
FROM `btggasify_purchase_live`.`tbl_purchaseorder_header`
WHERE MONTH(CreatedDate) = MONTH(CURDATE()) AND YEAR(CreatedDate) = YEAR(CURDATE());"""

try:
    parsed = sqlglot.parse(sql)
except Exception as e:
    print('GENERIC ERROR:', e)
