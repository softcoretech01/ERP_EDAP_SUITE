import logging
import networkx as nx
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.schema_models import SchemaRelationship

logger = logging.getLogger(__name__)

class RelationshipGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._is_loaded = False

    async def build_graph(self, db: AsyncSession, database_name: str = None):
        """Build the directed graph from SchemaRelationship table."""
        try:
            stmt = select(SchemaRelationship)
            # If we need to filter by DB, we would join SchemaTable, but for now load all globally or filter later
            result = await db.execute(stmt)
            relationships = result.scalars().all()
            
            self.graph.clear()
            for rel in relationships:
                # Add edges. Using target -> source typically for "Detail -> Header" or vice-versa
                # We add bi-directional edges with weights if needed, but undirected is better for shortest path joins
                self.graph.add_edge(rel.source_table, rel.target_table, 
                                    source_col=rel.source_column, 
                                    target_col=rel.target_column)
                self.graph.add_edge(rel.target_table, rel.source_table, 
                                    source_col=rel.target_column, 
                                    target_col=rel.source_column)
                
            self._is_loaded = True
            logger.info(f"Built relationship graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        except Exception as e:
            logger.error(f"Failed to build relationship graph: {e}")

    def find_join_path(self, start_table: str, end_table: str) -> Optional[List[Dict[str, str]]]:
        """Find the shortest join path between two tables."""
        if not self._is_loaded:
            logger.warning("Graph not loaded. Call build_graph first.")
            return None
            
        if start_table not in self.graph or end_table not in self.graph:
            return None
            
        try:
            path = nx.shortest_path(self.graph, source=start_table, target=end_table)
            joins = []
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                edge_data = self.graph.get_edge_data(u, v)
                joins.append({
                    "source_table": u,
                    "source_column": edge_data["source_col"],
                    "target_table": v,
                    "target_column": edge_data["target_col"]
                })
            return joins
        except nx.NetworkXNoPath:
            return None

    async def ensure_loaded(self, db: AsyncSession):
        """Ensure the graph is loaded, loading it if necessary."""
        if not self._is_loaded:
            await self.build_graph(db)

relationship_graph = RelationshipGraph()
