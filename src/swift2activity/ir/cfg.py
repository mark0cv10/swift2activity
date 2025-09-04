from typing import List, Tuple, Optional
from .nodes import Node

Edge = Tuple[int, int, Optional[str]]

class Graph:
    def __init__(self):
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []

    def add(self, node: Node) -> int:
        self.nodes.append(node)
        return len(self.nodes) - 1

    def link(self, a: int, b: int, label: str | None = None) -> None:
        self.edges.append((a, b, label))
