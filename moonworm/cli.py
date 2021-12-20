import argparse
import json
import os
from pathlib import Path
from shutil import copyfile

from web3.main import Web3
from web3.middleware import geth_poa_middleware

from moonworm.crawler.ethereum_state_provider import Web3StateProvider
from moonworm.watch import watch_contract

from .contracts import CU, ERC20, ERC721, CULands
from .crawler.networks import Network
from .generators.basic import (
    generate_contract_cli_content,
    generate_contract_interface_content,
)
from .generators.brownie import generate_brownie_interface


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


def handle_brownie_generate(args: argparse.Namespace):

    Path(args.outdir).mkdir(exist_ok=True)

    project_directory = args.project
    build_directory = os.path.join(project_directory, "build", "contracts")

    build_file_path = os.path.join(build_directory, f"{args.name}.json")
    if not os.path.isfile(build_file_path):
        raise IOError(
            f"File does not exist: {build_file_path}. Maybe you have to compile the smart contracts?"
        )

    with open(build_file_path, "r") as ifp:
        build = json.load(ifp)

    abi = build["abi"]
    interface = generate_brownie_interface(abi, args.name)
    write_file(interface, os.path.join(args.outdir, args.name + ".py"))


def handle_watch(args: argparse.Namespace) -> None:
    if args.abi == "erc20":
        contract_abi = ERC20.abi()
    elif args.abi == "erc721":
        contract_abi = ERC721.abi()
    elif args.abi == "cu":
        contract_abi = CU.abi()
    else:
        with open(args.abi, "r") as ifp:
            contract_abi = json.load(ifp)

    web3 = Web3(Web3.HTTPProvider(args.web3))
    if args.poa:
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    if args.db:
        if args.network is None:
            raise ValueError("Please specify --network")
        network = Network.__members__[args.network]
        from moonstreamdb.db import yield_db_session_ctx

        from .crawler.moonstream_ethereum_state_provider import (
            MoonstreamEthereumStateProvider,
        )

        state_provider = MoonstreamEthereumStateProvider(web3, network)

        with yield_db_session_ctx() as db_session:
            try:
                state_provider.set_db_session(db_session)
                watch_contract(
                    web3=web3,
                    state_provider=state_provider,
                    contract_address=web3.toChecksumAddress(args.contract),
                    contract_abi=contract_abi,
                    num_confirmations=args.confirmations,
                    start_block=args.start,
                )
            finally:
                state_provider.clear_db_session()

    else:

        watch_contract(
            web3=web3,
            state_provider=Web3StateProvider(web3),
            contract_address=web3.toChecksumAddress(args.contract),
            contract_abi=contract_abi,
            num_confirmations=args.confirmations,
            start_block=args.start,
        )


def handle_watch_cu(args: argparse.Namespace) -> None:
    from moonworm.cu_watch import watch_cu_contract

    MOONSTREAM_DB_URI = os.environ.get("MOONSTREAM_DB_URI")
    if not MOONSTREAM_DB_URI:
        print("Please set MOONSTREAM_DB_URI environment variable")
        return

    if args.abi is not None:
        with open(args.abi, "r") as ifp:
            contract_abi = json.load(ifp)
    else:
        print("Using CULand abi since no abi is specified")
        contract_abi = CULands.abi()

    web3 = Web3(Web3.HTTPProvider(args.web3))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    watch_cu_contract(
        web3,
        web3.toChecksumAddress(args.contract),
        contract_abi,
        args.confirmations,
        start_block=args.deployment_block,
        force_start=args.force,
    )


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Moonworm: Manage your smart contract")

    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers(dest="subcommands")

    watch_parser = subcommands.add_parser("watch", help="Watch a contract")
    watch_parser.add_argument(
        "-i",
        "--abi",
        required=True,
        help="ABI file path or 'erc20' or 'erc721' or cu",
    )

    watch_parser.add_argument(
        "-c",
        "--contract",
        required=True,
        help="Contract address",
    )

    watch_parser.add_argument(
        "-w",
        "--web3",
        required=True,
        help="Web3 provider",
    )

    watch_parser.add_argument(
        "--db",
        action="store_true",
        help="Use Moonstream database specified by 'MOONSTREAM_DB_URI' to get blocks/transactions. If set, need also provide --network",
    )

    watch_parser.add_argument(
        "--network",
        choices=Network.__members__,
        default=None,
        help="Network name that represents models from db. If --db is set, required",
    )

    watch_parser.add_argument(
        "--start",
        "-s",
        type=int,
        default=None,
        help="Block number to start watching from",
    )

    watch_parser.add_argument(
        "--poa",
        action="store_true",
        help="Pass this flag if u are using PoA network",
    )

    watch_parser.add_argument(
        "--confirmations",
        default=15,
        type=int,
        help="Number of confirmations to wait for. Default=12",
    )

    watch_parser.set_defaults(func=handle_watch)

    watch_cu_parser = subcommands.add_parser(
        "watch-cu", help="Watch a Crypto Unicorns contract"
    )
    watch_cu_parser.add_argument(
        "-i",
        "--abi",
        default=None,
        help="ABI file path, default is abi in  fixtures/abis/CU.json",
    )
    watch_cu_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force start from given block",
    )
    watch_cu_parser.add_argument(
        "-c",
        "--contract",
        required=True,
        help="Contract address",
    )

    watch_cu_parser.add_argument(
        "-w",
        "--web3",
        required=True,
        help="Web3 provider",
    )

    watch_cu_parser.add_argument(
        "--confirmations",
        default=10,
        type=int,
        help="Number of confirmations to wait for. Default=12",
    )

    watch_cu_parser.add_argument(
        "--deployment-block",
        "-d",
        type=int,
        help="Block number of the deployment",
    )

    watch_cu_parser.set_defaults(func=handle_watch_cu)

    generate_brownie_parser = subcommands.add_parser(
        "generate-brownie", description="Moonworm code generator for brownie projects"
    )
    generate_brownie_parser.add_argument(
        "-o",
        "--outdir",
        required=True,
        help=f"Output directory where files will be generated.",
    )
    generate_brownie_parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Prefix name for generated files",
    )
    generate_brownie_parser.add_argument(
        "-p",
        "--project",
        required=True,
        help=f"Path to brownie project directory",
    )
    generate_brownie_parser.set_defaults(func=handle_brownie_generate)

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
