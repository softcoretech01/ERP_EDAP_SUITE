import logging
import json
import re
import aiomysql
import time
from typing import Dict, Any, List, Optional
from ..services.llm_service import llm_service
from ..core.tenant_manager import tenant_manager
from ..core.config import settings

logger = logging.getLogger(__name__)

# Tables matching these patterns are noisy system tables — skip them entirely
SKIP_PATTERNS = [
    "log", "logs", "audit", "history", "temp", "tmp", "backup", "bak",
    "migration", "changelog", "session", "cache", "queue", "job",
    "__efmigrations", "sysdiagram", "dtproperties"
]

class SchemaAnalyzerAgent:
    def __init__(self):
        # Rule-based fast classification keywords
        self.rules = {
            "purchase": ["purchase", "supplier", "vendor", "procurement", "grn", "po_"],
            "sales": ["sales", "invoice", "salesorder", "packing", "returnorder", "quotation", "delivery", "dispatch"],
            "inventory": ["item", "product", "stock", "cylinder", "warehouse", "inventory", "batch", "bin"],
            "finance": ["finance", "payment", "ledger", "account", "receipt", "voucher", "journal", "tax", "gst"],
            "customer": ["customer", "cust", "party", "client", "debtor"],
            "hr": ["hr", "employee", "salary", "attendance", "payroll", "leave", "department"],
            "master": ["master", "type", "status", "roles", "users", "permissions", "config", "setting"],
            "system": ["log", "audit", "history", "temp", "backup", "migration", "changelog", "session"]
        }

    def _should_skip_table(self, table_name: str) -> bool:
        """Returns True if the table is a noisy system/log table that should be skipped."""
        t_lower = table_name.lower()
        for pattern in SKIP_PATTERNS:
            if pattern in t_lower:
                return True
        return False

    def _rule_based_classify(self, table_name: str) -> Optional[str]:
        t_lower = table_name.lower()
        for domain, keywords in self.rules.items():
            if any(kw in t_lower for kw in keywords):
                return domain
        return None

    async def _fetch_compact_metadata(self, host, port, user, password, db_name, table_name) -> Dict[str, Any]:
        """Fetch only column names and a few sample values — NOT the full CREATE TABLE statement."""
        result = {"columns": [], "sample_rows": []}
        try:
            pool = await aiomysql.create_pool(host=host, port=port, user=user, password=password, db=db_name)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Fetch column names only (lightweight)
                    await cur.execute(f"DESCRIBE `{table_name}`;")
                    desc_rows = await cur.fetchall()
                    result["columns"] = [row[0] for row in desc_rows]
                    
                    # Fetch 3 sample rows
                    await cur.execute(f"SELECT * FROM `{table_name}` LIMIT 3;")
                    rows = await cur.fetchall()
                    result["sample_rows"] = [list(row) for row in rows]
            pool.close()
            await pool.wait_closed()
        except Exception as e:
            logger.error(f"SchemaAnalyzer metadata fetch error on {db_name}.{table_name}: {e}")
        return result

    def _safe_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Safely extract JSON from LLM output that may contain extra text."""
        # Try direct parse first
        try:
            return json.loads(raw_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Strip markdown code fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            pass
        
        # Regex: find first { ... } block
        match = re.search(r'\{[^{}]*\}', raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Safe JSON parse failed. Raw LLM output (first 300 chars): {raw_text[:300]}")
        return None

    async def analyze_table(self, tenant_id: int, db_name: str, table_name: str, host: str, port: int, user: str, password: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # 0. Skip noisy tables immediately
        if self._should_skip_table(table_name):
            logger.info(f"SKIP noisy table: {db_name}.{table_name}")
            return {
                "tenant_id": tenant_id,
                "database": db_name,
                "table": table_name,
                "business_domain": "system",
                "purpose": f"System/log table (auto-skipped)",
                "important_columns": [],
                "relationships": [],
                "sample_values": [],
                "confidence": 100,
                "status": "pending_review"
            }
        
        # 1. Fetch compact metadata (NOT full CREATE TABLE)
        data = await self._fetch_compact_metadata(host, port, user, password, db_name, table_name)
        columns = data.get("columns", [])
        samples = data.get("sample_rows", [])
        
        # 2. Fast Rule-Based Classifier
        domain = self._rule_based_classify(table_name)
        confidence = 0
        
        if domain:
            confidence = 95
            logger.info(f"Rule-based match for {db_name}.{table_name} -> {domain} (skipping LLM)")
        
        # 3. LLM Fallback only if rule-based classification failed
        purpose = f"Stores data related to {domain}" if domain else "Unknown"
        important_columns = columns[:10] if columns else []
        
        if confidence < 90:
            # Build compact prompt — under 4000 chars
            compact_schema = json.dumps({
                "table_name": table_name,
                "database": db_name,
                "columns": columns[:30]  # Cap at 30 columns
            })
            
            # Truncate samples to keep prompt small
            sample_str = str(samples[:2])[:500]
            
            prompt = f"""Classify this ERP database table.

Table metadata:
{compact_schema}

Sample data (first 2 rows):
{sample_str}

Reply with ONLY this JSON:
{{
  "business_domain": "sales|purchase|inventory|finance|customer|hr|master|system|unknown",
  "purpose": "brief one-line description",
  "important_columns": ["col1", "col2"],
  "confidence": 85
}}"""
            
            try:
                resp = await llm_service.generate(
                    prompt=prompt, 
                    system="Output ONLY valid JSON. No explanations.", 
                    temperature=0.0,
                    num_predict=200  # Short response expected
                )
                
                parsed = self._safe_parse_json(resp)
                if parsed:
                    elapsed = time.time() - start_time
                    logger.info(f"LLM classified {db_name}.{table_name} -> {parsed.get('business_domain', 'unknown')} in {elapsed:.2f}s")
                    return {
                        "tenant_id": tenant_id,
                        "database": db_name,
                        "table": table_name,
                        "business_domain": parsed.get("business_domain", "unknown"),
                        "purpose": parsed.get("purpose", ""),
                        "important_columns": parsed.get("important_columns", columns[:10]),
                        "all_columns": columns,
                        "relationships": parsed.get("relationships", []),
                        "sample_values": [str(val) for row in samples for val in row if val and not isinstance(val, (int, float))][:5],
                        "confidence": parsed.get("confidence", 50),
                        "status": "pending_review"
                    }
                else:
                    logger.warning(f"LLM returned unparseable JSON for {db_name}.{table_name}, using fallback")
                    
            except Exception as e:
                logger.error(f"LLM classification failed for {db_name}.{table_name}: {e} — using fallback")
                # DO NOT raise — continue with fallback
                
        # 4. Return fallback/rule-based result (always succeeds)
        elapsed = time.time() - start_time
        logger.info(f"Schema analysis for {db_name}.{table_name} completed in {elapsed:.2f}s (domain={domain or 'unknown'})")
        return {
            "tenant_id": tenant_id,
            "database": db_name,
            "table": table_name,
            "business_domain": domain or "unknown",
            "purpose": purpose,
            "important_columns": important_columns,
            "all_columns": columns,
            "relationships": [],
            "sample_values": [str(val) for row in samples for val in row if val and not isinstance(val, (int, float))][:5],
            "confidence": confidence,
            "status": "pending_review"
        }

schema_analyzer_agent = SchemaAnalyzerAgent()
