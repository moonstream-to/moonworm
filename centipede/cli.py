import argparse
import json
import os

from .generator import generate_contract_cli_file, generate_contract_file


def handle_generate(args: argparse.Namespace) -> None:
    with open(args.abi, "r") as ifp:
        contract_abi = json.load(ifp)
    if args.interface:
        generate_contract_file(contract_abi, args.outdir)
    if args.cli:
        generate_contract_cli_file(contract_abi, args.outdir)


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centipede: Manage your smart contract"
    )

    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    generate_parser = subcommands.add_parser(
        "generate", description="Centipede code generator"
    )

    generate_parser.add_argument(
        "-i",
        "--abi",
        required=True,
        help=f"Path to contract abi JSON file",
    )
    generate_parser.add_argument(
        "-o",
        "--outdir",
        required=True,
        help=f"Output directory where files will be generated.",
    )
    generate_parser.add_argument(
        "--interface",
        action="store_true",
        help="Generate python interface for given smart contract abi",
    )

    generate_parser.add_argument(
        "--cli",
        action="store_true",
        help="Generate cli for given smart contract abi",
    )

    generate_parser.set_defaults(func=handle_generate)
    return parser


def main() -> None:
    parser = generate_argument_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
