from __future__ import annotations
from typing import Tuple
from ..ir.nodes import Initial, Final, Action, Decision, Merge
from ..ir.cfg import Graph

def _node_text(s: str | None) -> str:
    if not s:
        return ""
    s = " ".join(s.replace("\r", " ").replace("\n", " ").split())
    s = (s.replace("[", "(").replace("]", ")")
           .replace("{", "(").replace("}", ")")
           .replace('"', "'"))
    s = s.replace("\\(", "(").replace("\\)", ")")
    s = s.replace("(", "（").replace(")", "）")
    return s

def _edge_text(s: str | None) -> str:
    if not s:
        return ""
    s = " ".join(s.replace("\r", " ").replace("\n", " ").split())
    return s.replace("\\", "\\\\").replace('"', '\\"')

def _shape_and_raw(n) -> Tuple[str, str]:
    if isinstance(n, Initial):  return ("circle", "Start")
    if isinstance(n, Final):    return ("circle", "End")
    if isinstance(n, Decision): return ("diamond", getattr(n, "label", getattr(n, "cond", "cond?")))
    if isinstance(n, Merge):    return ("diamond", "merge")
    if isinstance(n, Action):   return ("box", getattr(n, "label", ""))
    return ("box", n.__class__.__name__)

def to_mermaid(g: Graph) -> str:
    lines = ["flowchart TD"]
    for i, n in enumerate(g.nodes):
        shape, raw = _shape_and_raw(n)
        txt = _node_text(raw)
        if shape == "circle":
            lines.append(f"    N{i}(({txt}))")
        elif shape == "diamond":
            lines.append(f"    N{i}{{{txt}}}")
        else:
            lines.append(f"    N{i}[{txt}]")

    for a, b, lbl in g.edges:
        if lbl:
            lines.append(f'    N{a} -- "{_edge_text(lbl)}" --> N{b}')
        else:
            lines.append(f"    N{a} --> N{b}")
    return "\n".join(lines)
