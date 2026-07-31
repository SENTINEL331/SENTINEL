def show_symbol_summary(symbol, data):
    """Display a summary of the latest market data."""

    latest = data.iloc[-1]

    print()
    print("=" * 50)
    print(symbol)
    print("=" * 50)

    print(f"Date       : {latest['Date']}")
    print(f"Close      : {latest['Close']:.2f}")

    if "SMA_20" in latest:
        print(f"SMA 20     : {latest['SMA_20']:.2f}")

    if "EMA_20" in latest:
        print(f"EMA 20     : {latest['EMA_20']:.2f}")

    print()