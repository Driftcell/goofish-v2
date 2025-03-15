import argparse

def main():
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI for the project.")
    
    parser.add_subparsers

    args = parser.parse_args()
    main()