import sqlglot

sql = """SELECT COUNT(*) AS PurchaseOrderCount
FROM `btggasify_purchase_live`.`tbl_purchaseorder_header`
WHERE MONTH(CreatedDate) = MONTH(CURDATE()) AND YEAR(CreatedDate) = YEAR(CURDATE());"""

try:
    parsed = sqlglot.parse(sql, read='mysql')
    print('SUCCESS 1')
except Exception as e:
    print('ERROR 1:', e)

try:
    parsed = sqlglot.parse_one(sql, read='mysql')
    print('SUCCESS 2')
except Exception as e:
    print('ERROR 2:', e)
