import logging
from typing import Dict, Any, List, Set, Tuple
import sqlglot
from sqlglot.expressions import Table, Column, Select, Delete, Update, Insert, Drop

logger = logging.getLogger(__name__)

class SQLValidator:
    def is_safe_sql(self, sql: str) -> bool:
        try:
            # Parse the SQL using sqlglot with mysql dialect
            parsed = sqlglot.parse(sql, read="mysql")
            for expression in parsed:
                # Disallow any mutation
                if isinstance(expression, (Delete, Update, Insert, Drop)):
                    logger.warning(f"Unsafe SQL detected: {type(expression)}")
                    return False
            return True
        except Exception as e:
            logger.error(f"SQL Parse error: {e}")
            return False

    async def validate_sql_against_schema(self, sql: str, schema_context_tables: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validates SQL against the retrieved schema context.
        Returns (is_valid, error_message)
        """
        if not self.is_safe_sql(sql):
            return False, "SQL is either invalid or contains unsafe operations (only SELECT is allowed)."

        try:
            parsed = sqlglot.parse_one(sql, read="mysql")
            
            # Extract allowed tables and columns from context
            allowed_tables = set()
            allowed_columns_per_table = {}
            for t in schema_context_tables:
                t_name = t["table_name"].lower()
                allowed_tables.add(t_name)
                allowed_columns_per_table[t_name] = set([c.lower() for c in t["columns"]])
            
            # 1. Validate Tables
            for table_expr in parsed.find_all(Table):
                t_name = table_expr.name.lower()
                if t_name not in allowed_tables:
                    return False, f"Table '{t_name}' is not in the allowed schema context."
            
            # 2. Validate Columns (basic validation)
            # If a column is fully qualified, we can check it. Otherwise we check if it exists in any allowed table.
            all_allowed_columns = set()
            for cols in allowed_columns_per_table.values():
                all_allowed_columns.update(cols)
                
            # Extract query aliases to real tables
            table_aliases = {}
            for table_expr in parsed.find_all(Table):
                t_name = table_expr.name.lower()
                alias = table_expr.alias.lower() if table_expr.alias else t_name
                table_aliases[alias] = t_name

            # Collect projection aliases to prevent them from failing validation when used in GROUP BY/ORDER BY
            aliases = set()
            for select in parsed.find_all(sqlglot.expressions.Select):
                for projection in select.expressions:
                    if isinstance(projection, sqlglot.expressions.Alias):
                        aliases.add(projection.alias.lower())

            for col_expr in parsed.find_all(Column):
                col_name = col_expr.name.lower()
                
                # If this column is just an alias reference, it's safe
                if col_name in aliases:
                    continue
                    
                table_ref = col_expr.table.lower() if col_expr.table else None
                
                # Check column
                if table_ref:
                    actual_table = table_aliases.get(table_ref, table_ref)
                    if actual_table not in allowed_columns_per_table:
                        return False, f"Table or alias '{table_ref}' used for column '{col_name}' is not defined in the query's FROM/JOIN clauses."
                        
                    if col_name not in allowed_columns_per_table[actual_table] and col_name != "*":
                        # Fuzzy match fallback
                        fuzzy_map = {c.replace("_", "").lower(): c for c in allowed_columns_per_table[actual_table]}
                        col_name_no_us = col_name.replace("_", "").lower()
                        if col_name_no_us in fuzzy_map:
                            col_expr.set("this", sqlglot.expressions.Identifier(this=fuzzy_map[col_name_no_us], quoted=True))
                            logger.info(f"Auto-corrected column '{col_name}' to '{fuzzy_map[col_name_no_us]}'")
                        else:
                            # Level 2: Synonym Resolver
                            from ..services.synonym_service import synonym_service
                            base_term = await synonym_service.normalize_term(col_name_no_us)
                            # Find any allowed column that maps to the same base term
                            mapped_col = None
                            for c in allowed_columns_per_table[actual_table]:
                                c_base = await synonym_service.normalize_term(c.replace("_", "").lower())
                                if c_base == base_term or (base_term in ["isactive", "issubmitted", "isdeleted"] and ("is" in c or "status" in c)):
                                    mapped_col = c
                                    break
                                    
                            if mapped_col:
                                col_expr.set("this", sqlglot.expressions.Identifier(this=mapped_col, quoted=True))
                                logger.info(f"Level 2 Synonym Mapped missing '{col_name}' to '{mapped_col}'")
                            else:
                                # Level 3: Strict Rejection
                                return False, f"BUSINESS_LOGIC_MAPPING_MISSING: Column '{col_name}' does not exist in table '{actual_table}'."
                else:
                    # Unqualified column. Try to infer table if only one table is used in the query.
                    query_tables = [t.name.lower() for t in parsed.find_all(Table)]
                    if len(set(query_tables)) == 1:
                        inferred_table = query_tables[0]
                        if inferred_table in allowed_columns_per_table:
                            if col_name not in allowed_columns_per_table[inferred_table] and col_name != "*":
                                # Fuzzy match fallback
                                fuzzy_map = {c.replace("_", "").lower(): c for c in allowed_columns_per_table[inferred_table]}
                                col_name_no_us = col_name.replace("_", "").lower()
                                if col_name_no_us in fuzzy_map:
                                    col_expr.set("this", sqlglot.expressions.Identifier(this=fuzzy_map[col_name_no_us], quoted=True))
                                    logger.info(f"Auto-corrected column '{col_name}' to '{fuzzy_map[col_name_no_us]}'")
                                else:
                                    # Level 2: Synonym Resolver
                                    from ..services.synonym_service import synonym_service
                                    base_term = await synonym_service.normalize_term(col_name_no_us)
                                    mapped_col = None
                                    for c in allowed_columns_per_table[inferred_table]:
                                        c_base = await synonym_service.normalize_term(c.replace("_", "").lower())
                                        if c_base == base_term or (base_term in ["isactive", "issubmitted", "isdeleted"] and ("is" in c or "status" in c)):
                                            mapped_col = c
                                            break
                                            
                                    if mapped_col:
                                        col_expr.set("this", sqlglot.expressions.Identifier(this=mapped_col, quoted=True))
                                        logger.info(f"Level 2 Synonym Mapped missing '{col_name}' to '{mapped_col}'")
                                    else:
                                        return False, f"BUSINESS_LOGIC_MAPPING_MISSING: Column '{col_name}' does not exist in table '{inferred_table}'."
                    else:
                        if col_name not in all_allowed_columns and col_name != "*":
                            # Fuzzy match fallback across all allowed columns
                            fuzzy_map = {c.replace("_", "").lower(): c for c in all_allowed_columns}
                            col_name_no_us = col_name.replace("_", "").lower()
                            if col_name_no_us in fuzzy_map:
                                col_expr.set("this", sqlglot.expressions.Identifier(this=fuzzy_map[col_name_no_us], quoted=True))
                                logger.info(f"Auto-corrected unqualified column '{col_name}' to '{fuzzy_map[col_name_no_us]}'")
                            else:
                                return False, f"BUSINESS_LOGIC_MAPPING_MISSING: Column '{col_name}' is not recognized in any allowed table."
                        
            corrected_sql = parsed.sql(dialect="mysql")
            return True, corrected_sql
            
        except sqlglot.errors.ParseError as e:
            return False, f"SQL syntax error: {e}"
        except Exception as e:
            logger.error(f"AST Validation error: {e}")
            return False, f"Validation error: {e}"

sql_validator = SQLValidator()
