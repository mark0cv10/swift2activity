from __future__ import annotations
from typing import Iterable, Optional
from antlr4 import ParserRuleContext
from ..ir.nodes import Initial, Final, Action, Decision, Merge
from ..ir.cfg import Graph


def _ctx_text(ctx: ParserRuleContext, tokens) -> str:
    try:
        return tokens.getText((ctx.start.tokenIndex, ctx.stop.tokenIndex))
    except Exception:
        try:
            return ctx.getText()
        except Exception:
            return ctx.__class__.__name__


class CFGBuilder:
    def build_from_tree(self, tree, tokens=None) -> Graph:
        g = Graph()
        start = g.add(Initial())
        end = g.add(Final())  

        func = self._find_first_by_name(tree, "function_declaration")
        body = self._call_child(func, "function_body")
        block = self._call_child(body, "code_block")

        if block is None:
            g.link(start, end)
            return g

        last = self._emit_block_linear(g, start, block, end_idx=end, tokens=tokens)

        if last is not None:
            g.link(last, end)
        return g

    def _emit_block_linear(
        self, g: Graph, entry_idx: int, code_block_ctx, end_idx: int,
        tokens=None, first_edge_label: Optional[str] = None
    ) -> Optional[int]:
        """
        Emituj code_block linearno: statement po statement.
        Redoslijed: for/while/repeat → if → return → action.
        - 'return' → veži na globalni End i prekini (vrati None)
        - first_edge_label (ako je zadat) ide NA PRVU ivicu u bloku
        """
        prev = entry_idx
        first = True

        for st in self._iter_statements(code_block_ctx):
            # ---- PETLJE
            inner_for = self._first_for_inside(st)
            if inner_for is not None:
                nxt = self._emit_for_in(
                    g, prev, inner_for, end_idx=end_idx, tokens=tokens,
                    incoming_label=(first_edge_label if first else None),
                )
                if nxt is None:
                    return None
                prev, first = nxt, False
                continue

            inner_while = self._first_while_inside(st)
            if inner_while is not None:
                nxt = self._emit_while(
                    g, prev, inner_while, end_idx=end_idx, tokens=tokens,
                    incoming_label=(first_edge_label if first else None),
                )
                if nxt is None:
                    return None
                prev, first = nxt, False
                continue

            inner_repeat = self._first_repeat_inside(st)
            if inner_repeat is not None:
                nxt = self._emit_repeat_while(
                    g, prev, inner_repeat, end_idx=end_idx, tokens=tokens,
                    incoming_label=(first_edge_label if first else None),
                )
                if nxt is None:
                    return None
                prev, first = nxt, False
                continue
            # ---- SWITCH
            inner_switch = self._first_switch_inside(st)
            if inner_switch is not None:
                nxt = self._emit_switch(
                    g, prev, inner_switch, end_idx=end_idx, tokens=tokens,
                    incoming_label=(first_edge_label if first else None),
                )
                if nxt is None:
                    return None
                prev, first = nxt, False
                continue
            # ---- IF
            inner_if = self._first_if_inside(st)
            if inner_if is not None:
                nxt = self._emit_if(
                    g, prev, inner_if, end_idx=end_idx, tokens=tokens,
                    incoming_label=(first_edge_label if first else None),
                )
                if nxt is None:
                    return None
                prev, first = nxt, False
                continue

            # ---- RETURN
            text = _ctx_text(st, tokens) or ""
            a = g.add(Action(_shorten_label(text)))
            if "return" in text:
                g.link(prev, a, first_edge_label if first else None)
                g.link(a, end_idx)
                return None

            # ---- OBIČAN STATEMENT
            g.link(prev, a, first_edge_label if first else None)
            prev, first = a, False
        return prev
    
    def _first_switch_inside(self, ctx):
        return (self._find_first_by_name(ctx, "switch_statement")
            or self._find_first_by_name(ctx, "switch"))
    def _iter_switch_cases(self, switch_ctx, tokens):
        """
        Vrati listu (label, body_ctx) za svaki case (+ default).
        Pokušava razne nazive iz različitih Swift3.g4 varijanti.
        """
        cases = []

        for sc in self._find_all_by_name(switch_ctx, "switch_case"):
            # label
            lbl_ctx = (self._call_child(sc, "case_label")
                    or self._call_child(sc, "switch_case_label")
                    or self._call_child(sc, "label")
                    or self._call_child(sc, "case_item_list")
                    or self._call_child(sc, "case_items"))
            lbl = _ctx_text(lbl_ctx, tokens) if lbl_ctx is not None else _ctx_text(sc, tokens)
            txt = " ".join((lbl or "").split())
            if txt.lower().startswith("case"):
                txt = txt[4:].lstrip(": ").strip()
            elif "default" in txt.lower():
                txt = "default"

            # tijelo
            body = (self._call_child(sc, "code_block")
                    or self._call_child(sc, "statements")
                    or sc)
            cases.append((txt or "default", body))

        for dc in self._find_all_by_name(switch_ctx, "default_label"):
            body = (self._call_child(dc, "code_block")
                    or self._call_child(dc, "statements")
                    or dc)
            cases.append(("default", body))

        return cases

    def _first_for_inside(self, ctx):
        return (self._find_first_by_name(ctx, "for_in_statement")
                or self._find_first_by_name(ctx, "for_statement")
                or None)

    def _first_while_inside(self, ctx):
        return self._find_first_by_name(ctx, "while_statement")

    def _first_repeat_inside(self, ctx):
        return (self._find_first_by_name(ctx, "repeat_while_statement")
                or self._find_first_by_name(ctx, "do_while_statement")
                or None)

    
    def _format_for_label(self, for_ctx, tokens) -> str:
        it = (self._call_child(for_ctx, "pattern")
            or self._call_child(for_ctx, "identifier")
            or self._call_child(for_ctx, "pattern_initializer"))
        seq = (self._call_child(for_ctx, "expression")
            or self._call_child(for_ctx, "expr")
            or self._call_child(for_ctx, "sequence_expression")
            or self._call_child(for_ctx, "binary_expressions"))
        it_txt = _ctx_text(it, tokens) if it is not None else "…"
        seq_txt = _ctx_text(seq, tokens) if seq is not None else "…"
        label = f"for {it_txt} in {seq_txt}"
        return _shorten_label(" ".join(label.split()))
    def _emit_switch(
        self, g: Graph, prev_idx: int, switch_ctx, end_idx: int, tokens=None,
        incoming_label: Optional[str] = None
    ) -> Optional[int]:
        expr = (self._call_child(switch_ctx, "expression")
                or self._call_child(switch_ctx, "expr"))
        d = g.add(Decision(_shorten_label(f"switch { _ctx_text(expr, tokens) if expr else '' }".strip())))
        g.link(prev_idx, d, incoming_label)

        branches = self._iter_switch_cases(switch_ctx, tokens)
        if not branches:
            m = g.add(Merge())
            g.link(d, m)
            return m

        outs = []
        for label, body in branches:
            last = self._emit_block_linear(
                g, d, body, end_idx=end_idx, tokens=tokens,
                first_edge_label=(f"case {label}" if label != "default" else "default")
            )
            if last is not None:
                outs.append(last)

        if not outs:
            return None

        m = g.add(Merge())
        for o in outs:
            g.link(o, m)
        return m

    def _emit_for_in(
        self, g: Graph, prev_idx: int, for_ctx, end_idx: int, tokens=None,
        incoming_label: Optional[str] = None
    ) -> Optional[int]:
        label = self._format_for_label(for_ctx, tokens)

        d = g.add(Decision(label))
        g.link(prev_idx, d, incoming_label)

        body = self._unwrap_to_code_block(for_ctx)
        last = None
        if body is not None:
            last = self._emit_block_linear(
                g, d, body, end_idx=end_idx, tokens=tokens, first_edge_label="yes"
            )
        if last is not None and last != d:
            g.link(last, d)

        m = g.add(Merge())
        g.link(d, m, "no")
        return m

    def _emit_while(
        self, g: Graph, prev_idx: int, while_ctx, end_idx: int, tokens=None,
        incoming_label: Optional[str] = None
    ) -> Optional[int]:
        cond = self._extract_if_condition(while_ctx, tokens)
        d = g.add(Decision(_shorten_label(cond)))
        g.link(prev_idx, d, incoming_label)

        body = self._unwrap_to_code_block(while_ctx)
        last = None
        if body is not None:
            last = self._emit_block_linear(
                g, d, body, end_idx=end_idx, tokens=tokens, first_edge_label="yes"
            )
        if last is not None and last != d:
            g.link(last, d)

        m = g.add(Merge())
        g.link(d, m, "no")
        return m


    def _emit_repeat_while(
        self, g: Graph, prev_idx: int, repeat_ctx, end_idx: int, tokens=None,
        incoming_label: Optional[str] = None
    ) -> Optional[int]:
        entry = g.add(Merge())
        g.link(prev_idx, entry, incoming_label)

        body = self._unwrap_to_code_block(repeat_ctx)
        last = entry
        if body is not None:
            last = self._emit_block_linear(g, entry, body, end_idx=end_idx, tokens=tokens)

        cond = self._extract_if_condition(repeat_ctx, tokens)
        d = g.add(Decision(_shorten_label(cond)))
        g.link(last if last is not None else entry, d)

        g.link(d, entry, "yes")

        m = g.add(Merge())
        g.link(d, m, "no")
        return m

    def _is_descendant(self, root, target) -> bool:
        if root is None or target is None:
            return False
        if root is target:
            return True
        for ch in getattr(root, "children", []) or []:
            if self._is_descendant(ch, target):
                return True
        return False

    def _emit_if(
        self, g: Graph, prev_idx: int, if_ctx, end_idx: int, tokens=None,
        incoming_label: Optional[str] = None
    ) -> Optional[int]:
        cond = self._extract_if_condition(if_ctx, tokens)
        d = g.add(Decision(_shorten_label(cond)))
        g.link(prev_idx, d, incoming_label)

        code_blocks = self._find_all_by_name(if_ctx, "code_block")
        then_block = code_blocks[0] if len(code_blocks) >= 1 else None

        else_holder = (
            self._call_child(if_ctx, "else_clause")
            or self._call_child(if_ctx, "alternative")
            or self._call_child(if_ctx, "else_block")
            or None
        )
        else_if_ctx = None
        if else_holder is not None:
            else_if_ctx = self._first_if_inside(else_holder)

        else_block = None
        if else_if_ctx is None:
            else_block = self._first_code_block_outside(if_ctx, then_block)

        then_last = d
        if then_block is not None:
            then_last = self._emit_block_linear(
                g, d, then_block, end_idx=end_idx, tokens=tokens, first_edge_label="yes"
            )

        else_last = None
        has_else = False
        if else_if_ctx is not None:
            has_else = True
            else_last = self._emit_if(
                g, d, else_if_ctx, end_idx=end_idx, tokens=tokens, incoming_label="no"
            )
        elif else_block is not None:
            has_else = True
            else_last = self._emit_block_linear(
                g, d, else_block, end_idx=end_idx, tokens=tokens, first_edge_label="no"
            )

        if has_else:
            if then_last is None and else_last is None:
                return None
            m = g.add(Merge())
            if then_last is not None:
                g.link(then_last, m)
            if else_last is not None:
                g.link(else_last, m)
            return m
        else:
            if then_last is None:
                return d  
            m = g.add(Merge())
            g.link(then_last, m)
            g.link(d, m) 
            return m


    def _unwrap_to_code_block(self, ctx):
        if ctx is None:
            return None
        blk = self._call_child(ctx, "code_block")
        if blk is not None:
            return blk
        return ctx

    def _extract_if_condition(self, if_ctx, tokens=None) -> str:
        for name in ("condition", "conditions", "expression", "if_condition", "guard_condition"):
            c = self._call_child(if_ctx, name)
            if c is not None:
                return _ctx_text(c, tokens)
        txt = _ctx_text(if_ctx, tokens)
        if txt.startswith("if"):
            txt = txt[2:].strip()
        cut = txt.find("{")
        return txt[:cut].strip() if cut > 0 else txt

    def _iter_statements(self, code_block_ctx) -> Iterable[ParserRuleContext]:
        if code_block_ctx is None:
            return []
        stmts = self._call_child(code_block_ctx, "statements")
        if stmts is not None:
            for ch in getattr(stmts, "children", []) or []:
                if ch and "statement" in ch.__class__.__name__.lower():
                    yield ch
            return
        for ch in getattr(code_block_ctx, "children", []) or []:
            if ch and "statement" in ch.__class__.__name__.lower():
                yield ch

    def _find_first_by_name(self, root, name: str):
        if root is None:
            return None
        cls = root.__class__.__name__.lower()
        if cls.startswith(name.lower()):
            return root
        for ch in getattr(root, "children", []) or []:
            found = self._find_first_by_name(ch, name)
            if found is not None:
                return found
        return None

    def _find_all_by_name(self, root, name: str):
        out = []
        if root is None:
            return out
        for ch in getattr(root, "children", []) or []:
            if not ch:
                continue
            cls = ch.__class__.__name__.lower()
            if cls.startswith(name.lower()):
                out.append(ch)
            out.extend(self._find_all_by_name(ch, name))
        return out

    def _first_if_inside(self, ctx):
        """Vrati prvi čvor koji predstavlja if/else-if bilo kojeg naziva."""
        if ctx is None:
            return None
        for ch in getattr(ctx, "children", []) or []:
            if not ch:
                continue
            cname = ch.__class__.__name__.lower()
            if "if" in cname:     
                return ch
        for ch in getattr(ctx, "children", []) or []:
            found = self._first_if_inside(ch)
            if found is not None:
                return found
        return None


    def _call_child(self, ctx, method_name: str):
        if ctx is None:
            return None
        if hasattr(ctx, method_name):
            member = getattr(ctx, method_name)
            try:
                return member()
            except TypeError:
                return member
        name_low = method_name.lower()
        for ch in getattr(ctx, "children", []) or []:
            if ch and ch.__class__.__name__.lower().startswith(name_low):
                return ch
        return None
    def _find_all_if_like(self, root):
        """Vrati SVE čvorove ispod 'root' čije ime klase sadrži 'if' (pokriva if + else-if varijante)."""
        out = []
        if root is None:
            return out
        for ch in getattr(root, "children", []) or []:
            if not ch:
                continue
            cname = ch.__class__.__name__.lower()
            if "if" in cname:
                out.append(ch)
            out.extend(self._find_all_if_like(ch))
        return out
    def _first_code_block_outside(self, root, exclude):
        """Prvi code_block ispod root-a koji NIJE potomak 'exclude' (korisno za 'else { ... }')."""
        for cb in self._find_all_by_name(root, "code_block"):
            if not self._is_descendant(exclude, cb):
                return cb
        return None

def _shorten_label(s: str, hard_limit: int = 60) -> str:
    s = " ".join((s or "").replace("\n", " ").split())
    return s if len(s) <= hard_limit else s[: hard_limit - 1] + "…"
