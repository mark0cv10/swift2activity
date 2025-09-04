class Node: pass

class Initial(Node):
    def __repr__(self): return "Initial"

class Final(Node):
    def __repr__(self): return "Final"

class Action(Node):
    def __init__(self, label: str): self.label = label
    def __repr__(self): return f"Action({self.label!r})"

class Decision(Node):
    def __init__(self, cond: str): self.cond = cond
    def __repr__(self): return f"Decision({self.cond!r})"

class Merge(Node):
    def __repr__(self): return "Merge"
