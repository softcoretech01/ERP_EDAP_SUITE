import asyncio
import re
from app.agents.sql_agent import sql_agent
from app.services.synonym_service import synonym_service

dashboard_questions = [
    "What is the total procurement spend this month?",
    "How much spend is under approval?",
    "What is the total committed spend?",
    "What is the total unpaid invoice value?",
    "Track procurement cycle from PR to Payment.",
    "Which PRs have not yet become Purchase Orders?",
    "Which POs have not yet been received?",
    "Which GRNs are pending invoice receipt?",
    "Which invoices are pending payment?",
    "Procurement cycle time.",
    "Average PR approval time.",
    "Average PO processing time.",
    "Supplier on-time delivery percentage.",
    "First-pass invoice matching rate.",
    "Procurement savings achieved.",
    "Show bottlenecks in procurement workflow.",
    "Which documents are pending beyond SLA?",
    "Show high-value pending approvals.",
    "Identify procurement process delays."
]

mock_schema = """
1. `tbl_purchaseorder_header`
Columns: poid, pono, podate, supplierid, createddt, subtotal, taxvalue, vatvalue, nettotal, isgrnraised, po_gm_isapproved, status
2. `tbl_PurchaseRequisition_Header`
Columns: prid, prno, prdate, ispoutil, pr_gm_isapproved, createddt, status
3. `tbl_irnreceipt_header`
Columns: receiptnote_hdr_id, irnno, irndate, paidamount, balance, status, createddt
4. `tbl_irnreceipt_detail`
Columns: receiptnote_dtl_id, receiptnote_hdr_id, itemid, qty, amount
5. `tbl_grn_header`
Columns: grnid, grnno, grndate, poid, createddt
6. `tbl_invoicereceipt_attachment`
Columns: attachmentid, receiptnote_hdr_id, filename
"""

async def test_all():
    print("Testing All Dashboard Questions LLM Generation\n")
    results = []
    
    synonym_service._load_defaults()
    synonym_service._is_loaded = True

    # Initialize file
    with open("dashboard_sql_results.md", "w", encoding="utf-8") as f:
        f.write("# Dashboard LLM Generation Results\n\n")

    for i, q in enumerate(dashboard_questions):
        print(f"[{i+1}/{len(dashboard_questions)}] Processing: {q}", flush=True)
        
        # 1. Get hints
        hints = await synonym_service.augment_query(q, "Procurement", mock_schema)
        
        # 2. Generate SQL directly using the SQL Agent
        try:
            sql = await sql_agent.generate_sql(
                query=q, 
                schema_context=mock_schema, 
                mapping_hints=hints
            )
            
            clean_sql = re.sub(r'```(?:sql)?', '', sql, flags=re.IGNORECASE).replace('```', '').strip()
            
            res_hints = hints.replace('BUSINESS MAPPING HINTS:', '').strip() if hints else "None"
            with open("dashboard_sql_results.md", "a", encoding="utf-8") as f:
                f.write(f"### Q: {q}\n")
                f.write(f"**Triggered Hints:**\n```\n{res_hints}\n```\n")
                f.write(f"**Generated SQL:**\n```sql\n{clean_sql}\n```\n")
                f.write("---\n")
        except Exception as e:
            with open("dashboard_sql_results.md", "a", encoding="utf-8") as f:
                f.write(f"### Q: {q}\n")
                f.write(f"**Generated SQL:**\nError: {e}\n---\n")

    print("\nFinished! Results saved to dashboard_sql_results.md", flush=True)

if __name__ == "__main__":
    asyncio.run(test_all())
