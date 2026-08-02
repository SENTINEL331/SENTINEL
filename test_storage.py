from ai.storage import Storage


def main():

    storage = Storage()

    records = storage.load_observations("NVDA")

    print()

    print("=" * 50)
    print("Stored Observations")
    print("=" * 50)

    print()

    print(f"Loaded : {len(records)}")

    print()

    for record in records:

        print(f"• {record.summary}")


if __name__ == "__main__":
    main()