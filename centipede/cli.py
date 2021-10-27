import argparse
import json
import os

from .generator import generate_contract_cli_file, generate_contract_file


def handle_genereate_interface(args: argparse.Namespace) -> None:
    with open(args.abi, "r") as ifp:
        contract_abi = json.load(ifp)
    generate_contract_file(contract_abi, args.output_path)


def handle_genereate_cli(args: argparse.Namespace) -> None:
    with open(args.abi, "r") as ifp:
        contract_abi = json.load(ifp)
    generate_contract_cli_file(contract_abi, args.output_path)


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centipede: Manage your smart contract"
    )

    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    generate_parser = subcommands.add_parser(
        "generate", description="Centipede code generator"
    )

    def populate_generate_leaf_parsers(
        leaf_parser: argparse.ArgumentParser,
    ) -> None:
        current_working_directory = os.getcwd()
        leaf_parser.add_argument(
            "-abi",
            "--abi",
            required=True,
            help=f"Path to contract abi JSON file",
        )
        leaf_parser.add_argument(
            "-op",
            "--output_path",
            default=current_working_directory,
            help=f"Output path where files will be generated. Default={current_working_directory}",
        )

    generate_parser.set_defaults(func=lambda _: generate_parser.print_help())

    genereate_subcommands = generate_parser.add_subparsers()
    generate_interface = genereate_subcommands.add_parser(
        "interface",
        description="Generate python interface for smart contract",
    )
    populate_generate_leaf_parsers(generate_interface)
    generate_interface.set_defaults(func=handle_genereate_interface)

    generate_cli = genereate_subcommands.add_parser(
        "cli",
        description="Generate python cli for smart contract",
    )
    populate_generate_leaf_parsers(generate_cli)
    generate_cli.set_defaults(func=handle_genereate_cli)
    return parser


def main() -> None:
    parser = generate_argument_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
