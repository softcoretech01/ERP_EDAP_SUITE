import asyncio
from app.services.synonym_service import synonym_service

questions = [
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

async def test_synonyms():
    # Load defaults
    synonym_service._load_defaults()
    synonym_service._is_loaded = True
    
    print("Testing Dashboard Hints mapped to Questions:\n")
    for q in questions:
        # Mock schema context just enough to trigger any column matching if needed, 
        # but dashboard hints don't depend on schema context for triggering
        mock_schema = "1. `tbl_purchaseorder_header`\nColumns: nettotal, poid\n2. `tbl_irnreceipt_header`\nColumns: paidamount, balance"
        hints = await synonym_service.augment_query(q, "Procurement", mock_schema)
        print(f"Q: {q}")
        if hints:
            print(f"HINTS: {hints.replace('BUSINESS MAPPING HINTS:', '').strip()}")
        else:
            print("HINTS: (No specific hints triggered)")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_synonyms())
