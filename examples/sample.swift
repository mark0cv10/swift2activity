func classify(_ x: Int) -> String {
    if x < 0 { return "neg" }
    else if x == 0 { return "zero" }
    else if x < 10 { return "small" }
    else if x < 100 { return "mid" }
    else { return "big" }
}
