import pandas as pd


def calculate(data, period=20, deviations=2):
    """
    Feature:
        Bollinger Bands

    Category:
        Volatility

    Purpose:
        Measures price relative to recent volatility.

    Inputs:
        Close

    Outputs:
        BB_MIDDLE
        BB_UPPER
        BB_LOWER
    """

    middle = data["Close"].rolling(window=period).mean()

    std = data["Close"].rolling(window=period).std()

    upper = middle + (std * deviations)

    lower = middle - (std * deviations)

    data["BB_MIDDLE"] = middle
    data["BB_UPPER"] = upper
    data["BB_LOWER"] = lower

    return data