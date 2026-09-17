"""
Entry point. Pick a channel to run:

    python main.py cli
    python main.py telegram
"""
import sys


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "cli"

    if channel == "cli":
        from channels.cli_channel import run
    elif channel == "telegram":
        from channels.telegram_channel import run
    else:
        print(f"Unknown channel: {channel}. Try 'cli' or 'telegram'.")
        sys.exit(1)

    run()


if __name__ == "__main__":
    main()
