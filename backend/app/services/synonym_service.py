import logging
from typing import List, Dict, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.schema_models import BusinessDictionary

logger = logging.getLogger(__name__)

class SynonymService:
    def __init__(self):
        # In-memory cache for fast resolution
        self._synonym_cache: Dict[str, str] = {}
        self._is_loaded = False

    async def load_synonyms(self, db: AsyncSession):
        """Load synonyms from the database into memory."""
        try:
            stmt = select(BusinessDictionary)
            result = await db.execute(stmt)
            dictionary_entries = result.scalars().all()
            
            self._synonym_cache.clear()
            for entry in dictionary_entries:
                base_term = entry.business_term.lower()
                self._synonym_cache[base_term] = entry.business_term
                
                if entry.synonyms:
                    for syn in entry.synonyms:
                        self._synonym_cache[syn.lower()] = entry.business_term
                        
            # Also load hardcoded defaults to bootstrap
            self._load_defaults()
            self._is_loaded = True
            logger.info(f"Loaded {len(self._synonym_cache)} synonyms.")
        except Exception as e:
            logger.error(f"Failed to load synonyms: {e}")
            self._load_defaults()

    def _load_defaults(self):
        defaults = {
            "quantity": ["qty", "reqqty", "requestedqty"],
            "amount": ["amount", "totalamount", "grandtotal"],
            "date": ["createddt", "entrydate", "prdate", "date", "createddate", "month", "created", "year", "today"],
            "purchase requisition": ["pr", "purchase request", "requisition", "requisitions",
                                     "requestion", "requision", "requsition", "requistition"],  # common typos
            "purchase order": ["po", "order"],
            "purchase": ["procurement"],
            "supplier": ["vendor", "vendors", "suppliers", "seller", "sellers"],
            "irn receipt": ["invoice", "invoices", "invoice receipt", "receipt note", "irn", "invoice receipt note"]
        }
        for base, syns in defaults.items():
            if base not in self._synonym_cache:
                self._synonym_cache[base] = base
            for syn in syns:
                if syn not in self._synonym_cache:
                    self._synonym_cache[syn] = base

    async def normalize_term(self, term: str, db: AsyncSession = None) -> str:
        if not self._is_loaded and db:
            await self.load_synonyms(db)
        elif not self._is_loaded:
            self._load_defaults()
            
        lower_term = term.lower()
        return self._synonym_cache.get(lower_term, term)

    async def augment_query(self, query: str, module: str, schema_context: str) -> str:
        """
        Schema-aware synonym detection.
        Detects keywords in the query, matches them against the dictionary,
        and searches the provided schema_context to map them directly to available columns.
        """
        import re
        if not self._is_loaded:
            self._load_defaults()
            
        query_lower = query.lower()
        
        # 1. Extract all columns and tables from schema_context
        schema_cols = set()
        schema_tables = set()
        for line in schema_context.split('\n'):
            line = line.strip()
            table_match = re.match(r'^\d+\.\s+`(?:[^`]+)`\s*\.\s*`([^`]+)`', line)
            if table_match:
                schema_tables.add(table_match.group(1).lower())
            else:
                table_match_no_db = re.match(r'^\d+\.\s+`([^`]+)`', line)
                if table_match_no_db:
                    schema_tables.add(table_match_no_db.group(1).lower())
                    
        for match in re.finditer(r'Columns:\s*(.*)', schema_context):
            cols = [c.strip().lower() for c in match.group(1).split(',')]
            schema_cols.update(cols)
            
        # 2. Find base terms present in query
        base_terms_in_query = set()
        for syn, base in self._synonym_cache.items():
            # Match word boundaries or exact phrase
            if re.search(rf'\b{re.escape(syn)}\b', query_lower):
                base_terms_in_query.add(base)
                
        # 3. For each base term, find matching schema columns
        hints = []
        for base in base_terms_in_query:
            # Get all synonyms for this base term
            all_syns = [k for k, v in self._synonym_cache.items() if v == base]
            
            # Check which syns exist in schema columns
            found_cols = [col for col in schema_cols if any(syn == col for syn in all_syns)]
            
            # If no direct match, check substring (e.g. 'totalamount' contains 'amount')
            if not found_cols:
                found_cols = [col for col in schema_cols if any(syn in col for syn in all_syns)]
                
            # Check which syns exist in schema tables
            found_tables = [tbl for tbl in schema_tables if any(syn in tbl or syn.replace(' ', '') in tbl for syn in all_syns)]
                
            if found_cols or found_tables:
                hint_parts = []
                if found_cols:
                    hint_parts.append(f"Columns: {', '.join(set(found_cols))}")
                if found_tables:
                    hint_parts.append(f"Tables: {', '.join(set(found_tables))}")
                hints.append(f"'{base}' maps to -> " + " | ".join(hint_parts))
            else:
                # Maybe it's an acronym expansion like PO -> Purchase Order
                used_syns = [k for k, v in self._synonym_cache.items() if v == base and re.search(rf'\b{re.escape(k)}\b', query_lower)]
                for s in used_syns:
                    if s != base:
                        hints.append(f"Use term '{base.title()}' when searching for '{s.upper()}'")
                        
        # 4. Inject explicit dashboard hints for complex KPIs
        dashboard_hints = {
            "committed spend": "Map 'committed spend' -> sum `tbl_purchaseorder_header.nettotal`",
            "unpaid invoice": "Map 'unpaid invoice' -> SUM(`tbl_irnreceipt_header`.`balance`)",
            "under approval": "Map 'under approval' -> check `po_gm_isapproved = 0` or `pr_gm_isapproved = 0`",
            "prs have not yet become": "Map 'PRs not POs' -> filter `tbl_PurchaseRequisition_Header.IsPOUtil = 0`",
            "pos have not yet been received": "Map 'POs not received' -> filter `tbl_purchaseorder_header.IsGrnRaised = 0`",
            "pending invoice receipt": "Map 'pending invoice receipt' -> GRNs without matching IRN",
            "pending payment": "Map 'pending payment' -> filter `tbl_irnreceipt_header.balance > 0`",
            "cycle time": "Map 'cycle time' -> calculate DATEDIFF(tbl_purchaseorder_header.podate, tbl_PurchaseRequisition_Header.prdate)",
            "approval time": "Map 'approval time' -> calculate AVG(DATEDIFF(prdate, createddt)) in tbl_PurchaseRequisition_Header",
            "processing time": "Map 'processing time' -> calculate AVG(DATEDIFF(podate, createddt)) in tbl_purchaseorder_header",
            "on-time delivery": "Map 'on-time delivery' -> compare tbl_grn_header.grndate and tbl_purchaseorder_header.podate without joining tbl_supplier",
            "savings": "Map 'savings' -> SUM(tbl_purchaseorder_header.subtotal - tbl_purchaseorder_header.nettotal)",
            "bottleneck": "Map 'bottleneck' -> identify documents pending beyond SLA or flagged as not utilized",
            "process delay": "Map 'process delay' -> identify documents pending beyond SLA",
            "beyond sla": "Map 'SLA breach' -> filter for documents where DATEDIFF(CURDATE(), createddt) > 7 and status is not complete"
        }
        
        for key, hint_text in dashboard_hints.items():
            if key in query_lower:
                hints.append(hint_text)

        if hints:
            return "BUSINESS MAPPING HINTS:\n" + "\n".join(set(hints))
        return ""

synonym_service = SynonymService()
