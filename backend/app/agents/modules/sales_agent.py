from ..base_sql_agent import BaseSQLAgent

class SalesAgent(BaseSQLAgent):
    def __init__(self):
        super().__init__()
        self.MODULE_NAME = "Sales"
        self.GLOBAL_INSTRUCTIONS = """
# 📈 SALES MODULE GLOBAL INSTRUCTIONS

When the user asks about the Sales Module (e.g., Sales Orders, Invoices, Customers), use these strict keyword mappings:

**Tables:**
- SO / Sales Order -> Look for `SalesOrder`, `SO_Header`, `SO_Detail`
- Invoice -> Look for `Invoice`, `Invoice_Header`, `Invoice_Detail`
- Customer -> Look for `Customer`, `Client`

**Columns:**
- **Date:** Map to `SalesDate`, `InvoiceDate`, `CreatedDate`, `DateCreated`, or `DocDate`.
- **Quantity:** Map to `Qty`, `Quantity`, `SoldQty`.
- **Amount:** Map to `Amount`, `TotalAmount`, `NetAmount`, or `GrandTotal`.
- **Status:** Map to `Status`, `PaymentStatus`, or `DocStatus`.
"""

sales_agent = SalesAgent()
