from ai.journal import ResearchJournal


def main():

    journal = ResearchJournal()

    print()

    print("=" * 50)
    print("Research Journal")
    print("=" * 50)

    print()

    print(
        journal.build("NVDA")
    )


if __name__ == "__main__":
    main()