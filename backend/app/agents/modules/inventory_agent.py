from ..base_sql_agent import BaseSQLAgent

class InventoryAgent(BaseSQLAgent):
    def __init__(self):
        super().__init__()
        self.MODULE_NAME = "Inventory"
        self.GLOBAL_INSTRUCTIONS = """
# 📦 INVENTORY MODULE GLOBAL INSTRUCTIONS

When the user asks about the Inventory Module (e.g., Items, Stock, Warehouses), use these strict keyword mappings:

**Tables:**
- Item / Product -> Look for `Item`, `Product`, `ItemMaster`
- Stock / Inventory -> Look for `Stock`, `Inventory`, `StockLedger`
- Warehouse -> Look for `Warehouse`, `Location`

**Columns:**
- **Date:** Map to `Date`, `TransactionDate`.
- **Quantity:** Map to `Qty`, `StockQty`, `AvailableQty`.
- **Status:** Map to `IsActive`, `Status`.
"""

inventory_agent = InventoryAgent()
