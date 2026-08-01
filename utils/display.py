def show_symbol_status(
    symbol,
    history_available,
    features_available,
):
    """Display the processing status for a symbol."""

    print()
    print("=" * 50)
    print(symbol)
    print("=" * 50)

    if history_available:
        print("✓ History Available")
    else:
        print("✗ History Missing")

    if features_available:
        print("✓ Features Available")
    else:
        print("✗ Features Missing")

    if history_available and features_available:
        print("✓ Ready for Research")

    print()


def show_summary(
    processed,
    ready,
    failed,
):
    """Display the processing summary."""

    print("=" * 40)
    print("Summary")
    print("=" * 40)

    print(f"Symbols Processed : {processed}")
    print(f"Ready             : {ready}")
    print(f"Failed            : {failed}")

    print()
    print("Market Module Complete")