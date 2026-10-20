import sys

from .app import Browser


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://text.npr.org"
    Browser(url).run()


if __name__ == "__main__":
    main()