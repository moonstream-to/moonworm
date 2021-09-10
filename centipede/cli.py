import argparse
import json
import os

from . import manage
from .generator import generate_contract_file


def handle_genereate_interface(args: argparse.Namespace) -> None:
    with open(args.abi, "r") as ifp:
        contract_abi = json.load(ifp)
    generate_contract_file(contract_abi, args.output_path)


def handle_contract_show(args: argparse.Namespace) -> None:
    with open(args.abi, "r") as ifp:
        contract_abi = json.load(ifp)
    show_all = not args.functions and not args.events
    functions, events = manage.abi_show(contract_abi)
    if show_all or args.functions:
        print("Functions:")
        for function in functions:
            print(f"function {function['name']}:")
            print("\tArgs:")
            for arg in function["inputs"]:
                print(f"\t\t{arg['name']} -> {arg['type']}")
            print("")
            print("\tReturns:")
            for out in function["outputs"]:
                print(f"\t\t{out['name']} -> {out['type']}")
            print("\n")

    if show_all or args.events:
        print("Events:")
        for event in events:
            print(f"event {event['name']}:")
            print("\tArgs:")
            for arg in event["inputs"]:
                print(f"\t\t{arg['name']} -> {arg['type']}")
            print("")


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Centipede: Manage your smart contract"
    )

    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers()

    contract = subcommands.add_parser("contract", description="Contract operations")
    contract.set_defaults(func=lambda _: contract.print_help())
    contract_subcommands = contract.add_subparsers()

    def populate_contract_leaf_parsers(
        leaf_parser: argparse.ArgumentParser,
    ) -> None:
        leaf_parser.add_argument(
            "-abi",
            "--abi",
            required=True,
            help=f"Path to contract abi JSON file",
        )

    contract_show = contract_subcommands.add_parser(
        "show", description="Show contract functions and events"
    )
    populate_contract_leaf_parsers(contract_show)
    contract_show.add_argument("--functions", action="store_true")
    contract_show.add_argument("--events", action="store_true")
    contract_show.set_defaults(func=handle_contract_show)

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

    return parser


def main() -> None:
    parser = generate_argument_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
