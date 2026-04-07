import argparse

def main():
    parser = argparse.ArgumentParser(description="Verdant Minds CLI")
    parser.add_argument("--help", action="store_true")
    args = parser.parse_args()
    print("Verdant Mind v0.4.0 — ready. Use 'verdant run' for cultivation.")

if __name__ == "__main__":
    main()
