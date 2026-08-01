import pandas as pd


def calculate(data, period=14):
    """
    Calculate Relative Strength Index (RSI).

    Category:
        Momentum

    Parameters:
        period (int): RSI lookback period.

    Returns:
        pandas.DataFrame
    """

    delta = data["Close"].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss

    data[f"RSI_{period}"] = 100 - (100 / (1 + rs))

    return data