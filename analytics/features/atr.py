import pandas as pd


def calculate(data, period=14):
    """
    Feature:
        Average True Range (ATR)

    Category:
        Volatility

    Purpose:
        Measures the average trading range over a given period.

    Inputs:
        High
        Low
        Close

    Outputs:
        ATR_14
    """

    previous_close = data["Close"].shift(1)

    tr = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    data[f"ATR_{period}"] = tr.rolling(window=period).mean()

    return data