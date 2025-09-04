from __future__ import annotations
from typing import Iterable, Optional
from antlr4 import ParserRuleContext
from ..ir.nodes import Initial, Final, Action, Decision, Merge
from ..ir.cfg import Graph


def _ctx_text(ctx: ParserRuleContext, tokens) -> str:
    """Vrati izvorni tekst konteksta iz token streama (ako je dostupan)."""
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

        func = self._find_first_by_name(tree, "function_declaration")
        body = self._call_child(func, "function_body")
        block = self._call_child(body, "code_block")

        if block is None:
            end = g.add(Final())
            g.link(start, end)
            return g

        last = self._emit_block_linear(g, start, block, tokens=tokens)

        if last is None:
            return g
        end = g.add(Final())
        g.link(last, end)
        return g

    def _emit_block_linear(self, g: Graph, entry_idx: int, code_block_ctx, tokens=None) -> Optional[int]:
        """
        Emituj code_block linearno: statement po statement.
        Vraća indeks zadnjeg čvora u liniji (ili None ako je dijagram već zatvoren return-om).
        """
        prev = entry_idx

        for st in self._iter_statements(code_block_ctx):
            name = st.__class__.__name__.lower()

            if name.startswith("if") or "if_statement" in name or name.endswith("ifstatementcontext"):
                prev = self._emit_if(g, prev, st, tokens)
                continue

            if "return" in _ctx_text(st, tokens).split():
                a = g.add(Action(_shorten_label(_ctx_text(st, tokens))))
                g.link(prev, a)
                final_idx = g.add(Final())
                g.link(a, final_idx)
                return None

            label = _shorten_label(_ctx_text(st, tokens))
            a = g.add(Action(label))
            g.link(prev, a)
            prev = a

        return prev

    def _emit_if(self, g: Graph, prev_idx: int, if_ctx, tokens=None) -> int:
        """Emituj if/else kao Decision → (then) … , (else) … → Merge; vrati indeks Merge čvora."""
        cond = self._extract_if_condition(if_ctx, tokens)
        d = g.add(Decision(_shorten_label(cond)))
        g.link(prev_idx, d)

        then_ctx = (
            self._call_child(if_ctx, "if_clause")
            or self._call_child(if_ctx, "consequence")
            or self._call_child(if_ctx, "then_clause")
            or if_ctx
        )
        else_ctx = (
            self._call_child(if_ctx, "else_clause")
            or self._call_child(if_ctx, "alternative")
            or self._call_child(if_ctx, "else_block")
            or None
        )

        then_block = self._unwrap_to_code_block(then_ctx)
        then_last = d
        if then_block is not None:
            then_last = self._emit_block_linear(g, d, then_block, tokens)
        g.link(d, then_last if then_last is not None else d, "yes")

        if else_ctx is not None:
            else_block = self._unwrap_to_code_block(else_ctx)
            else_last = d
            if else_block is not None:
                else_last = self._emit_block_linear(g, d, else_block, tokens)
            g.link(d, else_last if else_last is not None else d, "no")
            m = g.add(Merge())
            g.link(then_last if then_last is not None else d, m)
            g.link(else_last if else_last is not None else d, m)
            return m

        m = g.add(Merge())
        g.link(then_last if then_last is not None else d, m)
        g.link(d, m, "no")
        return m


    def _unwrap_to_code_block(self, ctx):
        """Vrati `code_block` unutar datog konteksta, ili sam kontekst ako već izgleda kao blok."""
        if ctx is None:
            return None
        blk = self._call_child(ctx, "code_block")
        if blk is not None:
            return blk
        return ctx

    def _extract_if_condition(self, if_ctx, tokens=None) -> str:
        """Izvuci tekst uslova iz if konteksta (robustan, više pokušaja)."""
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
        """Vrati sve statement čvorove iz code_block-a (razne varijante gramatike)."""
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
        """Nađi prvi podkontekst čije ime klase počinje sa `name` (case-insensitive)."""
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

    def _call_child(self, ctx, method_name: str):
        """Pozovi child-metodu ili pristupi polju ako postoji; inače pretraži djecu po imenu klase."""
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


def _shorten_label(s: str, hard_limit: int = 60) -> str:
    s = " ".join(s.replace("\n", " ").split())
    if len(s) <= hard_limit:
        return s
    return s[:hard_limit - 1] + "…"
