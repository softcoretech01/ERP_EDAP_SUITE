import os
import json
import logging
from datetime import datetime, timezone

class AuditLogger:
    def __init__(self, log_dir: str = "logs/audit"):
        # Make the audit logs directory inside the workspace
        # We can resolve relative to the backend app root
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "audit.log")
        
        # Configure local python logger for console output too
        self.logger = logging.getLogger("copilot.audit")
        self.logger.setLevel(logging.INFO)

    def log_query(self, user_id: int, tenant_id: int, question: str, sql: str = None, execution_time: float = 0.0):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "question": question,
            "sql": sql,
            "execution_time_seconds": round(execution_time, 3)
        }
        
        # Write to log file in JSON-lines format
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to audit log file: {e}")
            
        self.logger.info(f"[AUDIT] Tenant {tenant_id} | User {user_id} | Time: {log_entry['execution_time_seconds']}s | Question: {question}")

audit_logger = AuditLogger()
