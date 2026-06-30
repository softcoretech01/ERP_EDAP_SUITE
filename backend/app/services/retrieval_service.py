import logging
from typing import List, Dict, Any
from ..services.qdrant_service import qdrant_service
from ..services.synonym_service import synonym_service
from ..services.cache_service import cache_service

logger = logging.getLogger(__name__)

class RetrievalService:
    async def hybrid_search(self, tenant_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        # Check cache
        cache_key = f"hybrid_search:{tenant_id}:{query}:{limit}"
        cached = await cache_service.get(cache_key)
        if cached:
            logger.info("Hybrid search served from cache.")
            return cached
        # Normalize query using Synonym Engine
        # Strip punctuation and split into words
        import re
        query_clean = re.sub(r'[^\w\s]', '', query.lower())
        words = query_clean.split()
        normalized_words = [await synonym_service.normalize_term(w) for w in words]
        
        # Add singular forms for basic plurals, and spaceless versions for multi-word synonyms
        extended_words = set(normalized_words)
        for w in normalized_words:
            if w.endswith('s') and len(w) > 3:
                extended_words.add(w[:-1])
            if ' ' in w:
                extended_words.add(w.replace(' ', ''))
        
        print(f"extended_words: {extended_words}")
        normalized_query = " ".join(normalized_words)
        
        # 2. Vector Search using normalized query
        # We rely on Qdrant's vector search as the base mechanism
        vector_results = qdrant_service.search_vectors(
            collection_name="schema_collection",
            tenant_id=tenant_id,
            query=normalized_query,
            limit=limit * 5 # Fetch more for re-ranking
        )
        
        # 3. Hybrid Ranking (Vector Score + Keyword Score + Exact Match Score)
        ranked_results = []
        for i, result in enumerate(vector_results):
            table_name = (result.get("table_name") or result.get("table", "")).lower()
            business_name = result.get("business_domain", "").lower()
            keywords = [k.lower() for k in result.get("keywords", [])]
            
            exact_score = 0.0
            keyword_score = 0.0
            
            for word in extended_words:
                if word in table_name or word in business_name:
                    exact_score += 1.0
                if any(word in kw for kw in keywords):
                    keyword_score += 1.0
            
            # Bonus: prefer _header tables when doing aggregate/count queries
            # (header tables hold one record per document; detail tables hold line items)
            header_bonus = 0.3 if table_name.endswith('_header') else 0.0
            
            # Penalty: tbl_X_requisitions is a junction/link table, not the main requisition table
            # Penalise it when 'requisition' is in the user's extended words
            junction_penalty = 0.0
            if table_name.endswith('_requisitions') and 'requisition' in extended_words:
                junction_penalty = 0.5
            
            # Base vector score estimated by position in results
            vector_score = 1.0 - (i / max(len(vector_results), 1))
            
            final_score = (exact_score * 0.5) + (keyword_score * 0.3) + (vector_score * 0.2) + header_bonus - junction_penalty
            print(f"TABLE: {table_name} | exact: {exact_score} | kw: {keyword_score} | vec: {vector_score:.2f} | hdr: {header_bonus} | FINAL: {final_score:.3f}")
            
            ranked_results.append({
                "score": final_score,
                "payload": result
            })
            
        # Sort by final score descending
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Take top N uniquely by table
        final_payloads = []
        seen_tables = set()
        for x in ranked_results:
            table_name = (x["payload"].get("table_name") or x["payload"].get("table", "")).lower()
            if table_name and table_name not in seen_tables:
                seen_tables.add(table_name)
                final_payloads.append(x["payload"])
                if len(final_payloads) >= limit:
                    break
        
        logger.info(f"Hybrid retrieval returned {len(final_payloads)} unique tables.")
        
        # Save to cache
        await cache_service.set(cache_key, final_payloads, ttl_seconds=3600)
        
        return final_payloads

retrieval_service = RetrievalService()
