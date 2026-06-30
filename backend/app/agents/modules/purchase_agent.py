from ..base_sql_agent import BaseSQLAgent

class PurchaseAgent(BaseSQLAgent):
    def __init__(self):
        super().__init__()
        self.MODULE_NAME = "Purchase"
        self.GLOBAL_INSTRUCTIONS = """
==================================================
MODULE KNOWLEDGE: PURCHASE MODULE
=================================

Purchase module manages procurement lifecycle:
Purchase Requisition → Supplier Selection → Purchase Order → Goods Receipt → Invoice → Payment

Main entities:
* Purchase Requisition (PR)
* Purchase Order (PO)
* Supplier / Vendor
* Goods Receipt Note (GRN)
* Purchase Invoice
* Payment
* Purchase Return

Purchase-related keywords:
purchase, procurement, supplier, vendor, buying, purchase order, PO, PR, GRN, goods receipt, invoice, payment, vendor management

==================================================
TABLE SEMANTIC MAPPING
======================

1. PURCHASE REQUISITION TABLE
   Possible table names: purchase_requisition, pr_header, tbl_pr_header, purchase_request, material_request, indent_header
   Keywords: PR, purchase requisition, purchase request, material request, indent

2. PURCHASE ORDER HEADER TABLE
   Possible table names: tbl_purchaseorder_header, purchase_order, purchase_orders, po_header, po_hdr, po_master, purchaseorderheader
   Keywords: PO, purchase order, po header, po master
   Purpose: Stores purchase order main/header information.

3. PURCHASE ORDER DETAIL TABLE
   Possible table names: tbl_purchaseorder_detail, tbl_purchaseorder_details, po_items, po_detail, po_lines, purchase_order_items
   Keywords: po detail, po line, po items, purchase order detail
   Purpose: Stores line items of purchase order.

4. SUPPLIER TABLE
   Possible table names: supplier, suppliers, vendor, vendors, supplier_master, vendor_master, tbl_supplier
   Keywords: supplier, vendor, seller

5. GRN TABLE
   Possible table names: grn, goods_receipt, goods_receipt_note, grn_header, grn_master
   Keywords: GRN, goods receipt, received stock

6. PURCHASE INVOICE TABLE
   Possible table names: purchase_invoice, invoice, supplier_invoice, ap_invoice
   Keywords: purchase invoice, supplier invoice

==================================================
COLUMN SEMANTIC MAPPING (WARNING: ALWAYS CHECK EXACT NAME IN SCHEMA CONTEXT FIRST)
=======================
PO ID: poid, po_id, purchaseorderid, order_id, id
PO NUMBER: pono, po_no, ponumber, purchaseorderno, order_no
PO DATE: podate, po_date, order_date, purchase_date, document_date, transaction_date
Creation Date Column: createddt, created_at, createdon, createddate, inserted_at
Modified Date Column: modifieddt, modified_at, updated_at, updatedon
SUPPLIER ID: supplierid, supplier_id, vendorid, vendor_id, supplier_code, vendor_code
TOTAL AMOUNT: nettotal, grandtotal, totalamount, grand_total, net_amount, amount
SUBTOTAL: subtotal, sub_total, base_amount
DISCOUNT: discountvalue, discount_amount, discount
TAX: taxvalue, tax_amount
VAT: vatvalue, vat_amount
STATUS: status, isactive, approval_status, isapproved, isclosed
CANCEL STATUS: iscancel, is_cancel, cancelled, is_cancelled
GRN STATUS: isgrnraised, grn_status, goods_received, is_received
APPROVAL STATUS: po_gm_isapproved, po_director_isapproved, isapproved, approval_status

==================================================
BUSINESS RULES
==============

Approved PO: approval_status = 1 OR approved column = 1
Cancelled PO: cancel column = 1
Active PO: isactive = 1
GRN Pending: PO exists AND GRN not raised
GRN Completed: GRN raised = 1
Pending Approval: approval status = 0

==================================================
QUERY INTENT MAPPING
====================

COUNT Intent Keywords: count, how many, number of, total count -> SQL: COUNT(*)
SUM Intent Keywords: total value, purchase value, purchase amount, total purchase -> SQL: SUM(total_amount)
AVERAGE Intent Keywords: average, avg, mean -> SQL: AVG(total_amount)
GROUP BY Intent Keywords: supplier wise, vendor wise, monthly trend, yearly trend, department wise

==================================================
TIME FILTER MAPPING
===================

TODAY: today, current day -> SQL: DATE(date_column)=CURDATE()
YESTERDAY: yesterday -> SQL: DATE(date_column)=CURDATE()-INTERVAL 1 DAY
THIS WEEK: this week, weekly
THIS MONTH: this month, current month, monthly -> SQL: MONTH(date_column)=MONTH(CURDATE()) AND YEAR(date_column)=YEAR(CURDATE())
LAST MONTH: last month, previous month
THIS YEAR: this year, yearly, annual -> SQL: YEAR(date_column)=YEAR(CURDATE())

==================================================
SQL GENERATION RULES
====================

1. First identify business intent.
2. Detect relevant module.
3. Search vector DB for relevant schema.
4. Identify table using semantic meaning.
5. Identify columns using semantic meaning.
6. Generate SQL.
7. Validate SQL before execution.
8. Avoid hallucination.
9. Never assume columns exist.
10. Always check schema match before query generation.

IMPORTANT:
If multiple columns match same business meaning:
* Rank by semantic similarity
* Choose best matching column
"""

    def build_prompt(self, question, schema_context):
        return f"""
        {self.GLOBAL_INSTRUCTIONS}

        
        {schema_context}

        ============================
        USER QUESTION
        ============================
        {question}

        STRICT RULES:
        1. Use ONLY tables from schema context.
        2. Use ONLY columns from schema context.
        3. Never assume PRDate, created_at, etc.
        4. If column not found, choose closest semantic match.
        5. Return only valid SQL.
        
        OUTPUT FORMAT:
        1. User Intent
        2. Selected Module
        3. Selected Table
        4. Selected Columns
        5. SQL Validation Status
        6. Generated SQL:
        ```sql
        <query>
        ```
        """

purchase_agent = PurchaseAgent()
