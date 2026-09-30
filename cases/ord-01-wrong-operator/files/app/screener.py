"""추세 조건 8가지 판정."""


def passes_trend_template(s):
    """s: {price, ma50, ma150, ma200, ma200_slope, high_52w, low_52w}

    8개 조건을 모두 통과해야 True. 하나라도 어긋나면 False.
    """
    checks = [
        s["price"] > s["ma150"],
        s["price"] > s["ma200"],
        s["ma150"] < s["ma200"],
        s["ma200_slope"] > 0,
        s["price"] > s["ma50"],
        s["ma50"] > s["ma150"],
        s["price"] >= s["low_52w"] * 1.30,
        s["price"] >= s["high_52w"] * 0.75,
    ]
    return all(checks)
