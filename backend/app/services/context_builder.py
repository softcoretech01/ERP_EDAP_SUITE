import logging
from typing import List, Dict, Any
from ..services.relationship_graph import relationship_graph

logger = logging.getLogger(__name__)

class ContextBuilder:
    def build_schema_context(self, tables: List[Dict[str, Any]]) -> str:
        if not tables:
            return "No relevant schema found."
            
        module_name = tables[0].get("module", "Unknown")
        
        lines = []
        lines.append(f"Module: {module_name}\n")
        lines.append("Relevant Tables:")
        
        table_names = []
        
        import json
        idx = 1
        for table in tables:
            # Qdrant payloads have 'table' instead of 'table_name'
            t_names_str = table.get("table", table.get("table_name", f"Table_{idx}"))
            t_names_list = [t.strip() for t in t_names_str.split(",") if t.strip()]
            
            # Parse json_schema or fallback to 'columns' in payload
            cols = table.get("columns", [])
            json_str = table.get("json_schema", "")
            
            db_name = ""
            purpose = ""
            samples = []
            
            if json_str:
                try:
                    schema_obj = json.loads(json_str)
                    db_name = schema_obj.get("database", "")
                    purpose = schema_obj.get("purpose", "")
                    if not cols:
                        cols = schema_obj.get("all_columns", schema_obj.get("important_columns", []))
                    samples = schema_obj.get("sample_values", [])
                except Exception:
                    pass
                    
            for t_name in t_names_list:
                table_names.append(t_name)
                full_name = f"`{db_name}`.`{t_name}`" if db_name else f"`{t_name}`"
                lines.append(f"{idx}. {full_name}")
                if purpose:
                    lines.append(f"Purpose: {purpose}")
                if cols:
                    lines.append(f"Columns: {', '.join(cols)}")
                if samples:
                    lines.append(f"Sample Data: {', '.join(samples)}")
                lines.append("")
                idx += 1
            
        # Add Relationships
        lines.append("\nRelationships:")
        rels_found = 0
        for i in range(len(table_names)):
            for j in range(i + 1, len(table_names)):
                joins = relationship_graph.find_join_path(table_names[i], table_names[j])
                if joins:
                    for join in joins:
                        lines.append(f"{join['source_table']}.{join['source_column']} = {join['target_table']}.{join['target_column']}")
                        rels_found += 1
                        
        if rels_found == 0:
            lines.append("No direct relationships found between these tables.")
            
        context_str = "\n".join(lines)
        logger.info(f"Built schema context with {len(tables)} tables and {rels_found} relationships.")
        return context_str

context_builder = ContextBuilder()
