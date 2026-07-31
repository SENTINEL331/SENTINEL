def calculate(data, period):
    """Calculate a Simple Moving Average."""

    data = data.copy()

    data[f"SMA_{period}"] = (
        data["Close"]
        .rolling(window=period)
        .mean()
    )

    return data