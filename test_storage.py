from ai.storage import Storage


def main():

    storage = Storage()

    observations = storage.load_observations("NVDA")

    print()

    print("=" * 50)
    print("Stored Observations")
    print("=" * 50)

    print()

    print(f"Loaded : {len(observations)}")

    print()

    for observation in observations:

        print(f"• {observation.statement}")


if __name__ == "__main__":
    main()