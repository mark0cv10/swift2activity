from ..ir.nodes import Initial, Final, Action, Decision, Merge
from ..ir.cfg import Graph

def _node_label(node):
    if isinstance(node, Initial):  return ("circle", "Start")
    if isinstance(node, Final):    return ("circle", "End")
    if isinstance(node, Decision): return ("diamond", getattr(node, "cond", "cond?"))
    if isinstance(node, Merge):    return ("diamond", "merge")
    if isinstance(node, Action):   return ("box", getattr(node, "label", ""))
    return ("box", node.__class__.__name__)

def to_mermaid(g: Graph) -> str:
    lines = ["flowchart TD"]
    for i, n in enumerate(g.nodes):
        shape, text = _node_label(n)
        # malo “čišćenje” da ne zeznu parser
        safe = (text or "").replace("[", "(").replace("]", ")")
        safe = safe.replace("\n", " ").strip()

        if shape == "circle":
            # ✅ krug je ((...)) — bez kvadratnih zagrada
            lines.append(f"    N{i}(({safe}))")
        elif shape == "diamond":
            lines.append(f"    N{i}{{{safe}}}")
        else:  # box
            lines.append(f"    N{i}[{safe}]")

    for a, b, lbl in g.edges:
        if lbl:
            lines.append(f"    N{a} -->|{lbl}| N{b}")
        else:
            lines.append(f"    N{a} --> N{b}")

    return "\n".join(lines)
