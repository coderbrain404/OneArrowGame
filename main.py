"""一箭又一箭——程序入口。"""

try:
    from ui import ArrowGame
except ModuleNotFoundError as error:
    if error.name == "pygame":
        raise SystemExit(
            "Pygame is not installed in this Python environment. Run: "
            "py -3.13 -m pip install -r requirements.txt"
        ) from error
    raise


def main() -> None:
    ArrowGame().run()


if __name__ == "__main__":
    main()
