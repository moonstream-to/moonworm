import argparse
import json
import os
from pathlib import Path
from shutil import copyfile

from .contracts import ERC20, ERC721
from .generator import (
    generate_contract_cli_content,
    generate_contract_interface_content,
)


def write_file(content: str, path: str):
    with open(path, "w") as ofp:
        ofp.write(content)


def copy_web3_util(dest_dir: str, force: bool = False) -> None:
    dest_filepath = os.path.join(dest_dir, "web3_util.py")
    if os.path.isfile(dest_filepath) and not force:
        print(f"{dest_filepath} file already exists. Use -f to rewrite")
    web3_util_path = os.path.join(os.path.dirname(__file__), "web3_util.py")
    copyfile(web3_util_path, dest_filepath)


def create_init_py(dest_dir: str, force: bool = False) -> None:
    dest_filepath = os.path.join(dest_dir, "__init__.py")
    if os.path.isfile(dest_filepath) and not force:
        print(f"{dest_filepath} file already exists. Use -f to rewrite")
    with open(dest_filepath, "w") as ofp:
        ofp.write("")


def handle_generate(args: argparse.Namespace) -> None:
    if not args.interface and not args.cli:
        print("Please specify what you want to generate:")
        print("--interface for smart contract interface")
        print("--cli for smart contract cli")
        return
    Path(args.outdir).mkdir(exist_ok=True)

    args.name = args.name + "_"

    if args.abi == "erc20":
        contract_abi = ERC20.abi()
        write_file(
            ERC20.bytecode(), os.path.join(args.outdir, args.name + "bytecode.bin")
        )
    elif args.abi == "erc721":
        contract_abi = ERC721.abi()
        write_file(
            ERC721.bytecode(), os.path.join(args.outdir, args.name + "bytecode.bin")
        )
    else:
        with open(args.abi, "r") as ifp:
            contract_abi = json.load(ifp)

    abi_file_name = args.name + "abi.json"
    write_file(json.dumps(contract_abi), os.path.join(args.outdir, abi_file_name))
    copy_web3_util(args.outdir, args.force)
    create_init_py(args.outdir, args.force)
    if args.interface:
        interface_content = generate_contract_interface_content(
            contract_abi, abi_file_name
        )
        interface_name = args.name + "interface.py"
        write_file(interface_content, os.path.join(args.outdir, interface_name))
    if args.cli:
        cli_content = generate_contract_cli_content(contract_abi, abi_file_name)
        cli_name = args.name + "cli.py"
        write_file(cli_content, os.path.join(args.outdir, cli_name))
    print(f"Files are successfully generated to:{args.outdir}")


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Moonworm: Manage your smart contract")

    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers(dest="subcommands")

    generate_parser = subcommands.add_parser(
        "generate", description="Moonworm code generator"
    )

    generate_parser.add_argument(
        "-i",
        "--abi",
        required=True,
        help=f"Path to contract abi JSON file or (erc20|erc721)",
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
    generate_parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Prefix name for generated files",
    )
    generate_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force rewrite generated files",
    )
    generate_parser.set_defaults(func=handle_generate)
    return parser


def main() -> None:
    parser = generate_argument_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
