import argparse
from antlr4 import FileStream, CommonTokenStream
from ..support.Swift3LexerEx import Swift3LexerEx
from ..support.Swift3ParserEx import Swift3ParserEx

class TokenStreamAdapter:
    class _TokenWithGetType:
        def __init__(self, tok):
            self._tok = tok
        def getType(self):
            # Python runtime koristi .type umjesto getType()
            return getattr(self._tok, "type", None)
        def __getattr__(self, name):
            return getattr(self._tok, name)

    def __init__(self, ts):
        self.ts = ts

    # parser očekuje METODU index()
    def index(self):
        try:
            return self.ts.index
        except Exception:
            return self.ts.index()

    def LA(self, i):
        return self.ts.LA(i)

    def LT(self, i):
        return self.ts.LT(i)

    def get(self, i):
        # vrati wrapper sa .getType()
        return self._TokenWithGetType(self.ts.get(i))

    def getText(self, interval=None):
        try:
            return self.ts.getText(interval)
        except TypeError:
            return self.ts.getText()

    def __getattr__(self, name):
        return getattr(self.ts, name)

from ..frontend.ast_visitor import CFGBuilder
from ..emitters.mermaid import to_mermaid


def parse_file(path: str):
    input_stream = FileStream(path, encoding="utf-8")
    lexer = Swift3LexerEx(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = Swift3ParserEx(tokens)

    import generated.Swift3Parser as S3P
    import generated.Swift3Lexer as S3L
    from SwiftSupport import SwiftSupport as _SwiftSupport

    S3P.SwiftSupport = _SwiftSupport
    S3P._input = TokenStreamAdapter(parser._input)

    LexCls = S3L.Swift3Lexer

    def _tok_id(name: str):
        val = getattr(LexCls, name, None)
        if val is not None:
            return val
        try:
            return LexCls.symbolicNames.index(name)
        except Exception:
            return None

    for _name in getattr(LexCls, "symbolicNames", []) or []:
        if not _name or not _name.isidentifier():
            continue
        _val = _tok_id(_name)
        if _val is not None and not hasattr(S3P, _name):
            setattr(S3P, _name, _val)

    if not hasattr(S3P, "WS"):
        raise RuntimeError("Swift3Lexer nema token 'WS' – provjeri naziv whitespace tokena u lekserskoj gramatici.")


    if hasattr(parser, "top_level"):
        tree = parser.top_level()
    else:
        for rule in ("compilation_unit", "source", "program", "translation_unit"):
            if hasattr(parser, rule):
                tree = getattr(parser, rule)()
                break
        else:
            raise RuntimeError("Nepoznat start rule za Swift3.g4")

    return tree, tokens



def main():
    ap = argparse.ArgumentParser(description="Swift -> UML Activity (Mermaid)")
    ap.add_argument("input", help="Swift file")
    ap.add_argument("-o", "--output", default="out.mmd")
    args = ap.parse_args()

    tree, tokens = parse_file(args.input)
    cfg = CFGBuilder().build_from_tree(tree, tokens=tokens)
    mmd = to_mermaid(cfg)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(mmd)
    print(f"OK: napisao {args.output}")


if __name__ == "__main__":
    main()
