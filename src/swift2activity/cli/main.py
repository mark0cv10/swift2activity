import argparse
from antlr4 import FileStream, CommonTokenStream
from ..support.Swift3LexerEx import Swift3LexerEx
from ..support.Swift3ParserEx import Swift3ParserEx

class TokenStreamAdapter:
    def __init__(self, ts):
        self.ts = ts
    def index(self):
        return self.ts.index
    def LA(self, i):
        return self.ts.LA(i)
    def LT(self, i):
        return self.ts.LT(i)

from ..frontend.ast_visitor import CFGBuilder
from ..emitters.mermaid import to_mermaid


def parse_file(path: str):
    input_stream = FileStream(path, encoding="utf-8")
    lexer = Swift3LexerEx(input_stream)
    tokens = CommonTokenStream(lexer)
    parser = Swift3ParserEx(tokens)

    import generated.Swift3Parser as S3P
    from SwiftSupport import SwiftSupport as _SwiftSupport
    S3P.SwiftSupport = _SwiftSupport
    S3P._input = TokenStreamAdapter(parser._input)

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
