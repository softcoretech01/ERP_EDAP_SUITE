from ..base_sql_agent import BaseSQLAgent

class FinanceAgent(BaseSQLAgent):
    def __init__(self):
        super().__init__()
        self.MODULE_NAME = "Finance"
        self.GLOBAL_INSTRUCTIONS = """
# 💰 FINANCE MODULE GLOBAL INSTRUCTIONS

When the user asks about the Finance Module (e.g., Accounts, Ledgers, Balances), use these strict keyword mappings:

**Tables:**
- Account / Ledger -> Look for `Account`, `Ledger`, `ChartOfAccounts`
- Transaction -> Look for `Transaction`, `JournalEntry`
- Payment -> Look for `Payment`, `Receipt`

**Columns:**
- **Date:** Map to `TransactionDate`, `PaymentDate`, `Date`.
- **Amount:** Map to `Amount`, `Debit`, `Credit`, `Balance`.
- **Type:** Map to `TransactionType`, `AccountType`.
"""

finance_agent = FinanceAgent()
