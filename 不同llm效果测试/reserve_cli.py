import argparse
from getpass import getpass
from typing import Optional

from seat_reserver import reserve_seat


def main() -> None:
    parser = argparse.ArgumentParser(description="Reserve a library seat.")
    parser.add_argument("--username", required=True, help="Library account username")
    parser.add_argument("--password", help="Library account password (omit to prompt)")
    parser.add_argument("--target-area", help="Target area name or code (A/B)")
    parser.add_argument(
        "--target-seat-no",
        type=int,
        help="Seat number within the target area. Leave blank to auto-search.",
    )
    parser.add_argument(
        "--config",
        default="seat_reserver.ini",
        help="Path to configuration template (default: seat_reserver.ini)",
    )
    args = parser.parse_args()

    password = args.password or getpass("Password: ")
    result = reserve_seat(
        username=args.username,
        password=password,
        target_area=args.target_area,
        target_seat_no=args.target_seat_no,
        config_path=args.config,
    )
    print("Reservation result:", result)


if __name__ == "__main__":
    main()

