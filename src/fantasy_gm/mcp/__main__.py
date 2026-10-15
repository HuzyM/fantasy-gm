"""Run the local stdio server: python -m fantasy_gm.mcp."""

from fantasy_gm.mcp.server import create_server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
