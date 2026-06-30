import re
schema = """
Module: Purchase

Relevant Tables:
1. `erp_db`.`tbl_purchaseorder_header`
Purpose: Master relationship rules...
Columns: poid, pono, podate, supplierid, createddt, subtotal, taxvalue, vatvalue, nettotal, isgrnraised, po_gm_isapproved, status
Sample Data: ...
"""

tables_in_context = []
current_table = None
for line in schema.split('\n'):
    line = line.strip()
    table_match = re.match(r'^\d+\.\s+`(?:[^`]+)`\s*\.\s*`([^`]+)`', line)
    if table_match:
        current_table = table_match.group(1)
        tables_in_context.append({'table_name': current_table, 'columns': []})
    elif not table_match:
        table_match_no_db = re.match(r'^\d+\.\s+`([^`]+)`', line)
        if table_match_no_db:
            current_table = table_match_no_db.group(1)
            tables_in_context.append({'table_name': current_table, 'columns': []})
        elif line.startswith('Columns:') and current_table:
            cols_str = line.replace('Columns:', '').strip()
            cols = [c.strip() for c in cols_str.split(',')]
            tables_in_context[-1]['columns'].extend(cols)

print(tables_in_context)
