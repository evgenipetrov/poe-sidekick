"""Main entry point for POE Sidekick."""

from poe_sidekick.core.window import GameWindow


def main() -> None:
    """Start the POE Sidekick application."""
    window = GameWindow()
    if window.find_window():
        window.bring_to_front()
    else:
        print("Path of Exile 2 window not found")


if __name__ == "__main__":
    main()
