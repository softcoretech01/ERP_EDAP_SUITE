import asyncio
from app.agents.sql_agent import sql_agent

async def run():
    try:
        from app.db.database import SessionLocal
        from sqlalchemy import text
        async with SessionLocal() as session:
            result = await session.execute(text("SELECT PR_Number, IsPOUtil, po_ref_id FROM tbl_PurchaseRequisition_Header LIMIT 10;"))
            rows = result.fetchall()
            print("--- PR SAMPLE ---")
            for r in rows:
                print(r)
                
            result2 = await session.execute(text("SELECT COUNT(*) FROM tbl_PurchaseRequisition_Header WHERE IsPOUtil = 0;"))
            print(f"PRs with IsPOUtil = 0: {result2.scalar()}")
            
            result3 = await session.execute(text("SELECT COUNT(*) FROM tbl_PurchaseRequisition_Header WHERE po_ref_id IS NULL;"))
            print(f"PRs with po_ref_id IS NULL: {result3.scalar()}")
    except Exception as e:
        print(f"Failed to query DB: {e}")

if __name__ == "__main__":
    asyncio.run(run())
