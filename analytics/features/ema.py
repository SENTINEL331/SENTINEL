def calculate(data, period=20):
    """
    Calculate Exponential Moving Average (EMA).

    Category:
        Trend

    Purpose:
        Gives greater weight to recent prices than SMA.

    Parameters:
        period (int): Lookback period.

    Returns:
        pandas.DataFrame
    """

    column = f"EMA_{period}"

    data[column] = (
        data["Close"]
        .ewm(span=period, adjust=False)
        .mean()
    )

    return data