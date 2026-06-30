from ..base_sql_agent import BaseSQLAgent

class HRAgent(BaseSQLAgent):
    def __init__(self):
        super().__init__()
        self.MODULE_NAME = "HR"
        self.GLOBAL_INSTRUCTIONS = """
# 👥 HR MODULE GLOBAL INSTRUCTIONS

When the user asks about the HR Module (e.g., Employees, Payroll, Attendance), use these strict keyword mappings:

**Tables:**
- Employee -> Look for `Employee`, `Staff`, `User`
- Payroll / Salary -> Look for `Payroll`, `Salary`, `Payslip`
- Attendance -> Look for `Attendance`, `Timesheet`

**Columns:**
- **Date:** Map to `JoinDate`, `Date`, `Month`.
- **Amount:** Map to `Salary`, `NetPay`, `GrossPay`.
- **Status:** Map to `IsActive`, `EmploymentStatus`.
"""

hr_agent = HRAgent()
