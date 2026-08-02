from sentinel.sentinel import Sentinel


def main():

    sentinel = Sentinel()

    snapshot = sentinel.get_snapshot("NVDA")

    print()
    print("=" * 50)
    print("Snapshot")
    print("=" * 50)
    print()

    print(snapshot.to_text())


if __name__ == "__main__":
    main()