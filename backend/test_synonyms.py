import asyncio
import os
import sys
import re
sys.path.insert(0, os.path.abspath('.'))
from app.services.synonym_service import synonym_service

async def test():
    query='how many invoices were received this month'
    query_clean=re.sub(r'[^\w\s]', '', query.lower())
    words=query_clean.split()
    norm=[await synonym_service.normalize_term(w) for w in words]
    print(norm)

asyncio.run(test())
