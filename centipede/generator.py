import json
import logging
import os
from typing import Any, Dict, List, Union
from shutil import copyfile
import keyword

import libcst as cst
from web3.types import ABIFunction

from .version import CENTIPEDE_VERSION

CONTRACT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "contract.py.template")
try:
    with open(CONTRACT_TEMPLATE_PATH, "r") as ifp:
        REPORTER_FILE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(
        f"WARNING: Could not load reporter template from {CONTRACT_TEMPLATE_PATH}:"
    )
    logging.warn(e)

CLI_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "cli.py.template")
try:
    with open(CLI_TEMPLATE_PATH, "r") as ifp:
        CLI_FILE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(f"WARNING: Could not load reporter template from {CLI_TEMPLATE_PATH}:")
    logging.warn(e)


def make_annotation(types: list):
    if len(types) == 1:
        return cst.Annotation(annotation=cst.Name(types[0]))
    union_slice = []
    for _type in types:
        union_slice.append(
            cst.SubscriptElement(
                slice=cst.Index(
                    value=cst.Name(_type),
                )
            ),
        )
    return cst.Annotation(
        annotation=cst.Subscript(value=cst.Name("Union"), slice=union_slice)
    )


def normalize_abi_name(name: str) -> str:
    if keyword.iskeyword(name):
        return name + "_"
    else:
        return name


def python_type(evm_type: str) -> List[str]:
    if evm_type.startswith(("uint", "int")):
        return ["int"]
    elif evm_type.startswith("bytes"):
        return ["bytes"]
    elif evm_type == "string":
        return ["str"]
    elif evm_type == "address":
        return ["ChecksumAddress", "Address"]
    elif evm_type == "bool":
        return ["bool"]
    else:
        raise ValueError(f"Cannot convert to python type {evm_type}")


def generate_contract_class(
    abi: Dict[str, Any],
) -> cst.ClassDef:
    class_name = "Contract"
    class_constructor = cst.FunctionDef(
        name=cst.Name("__init__"),
        body=cst.IndentedBlock(
            body=[
                cst.parse_statement("self.web3 = web3"),
                cst.parse_statement("self.address = contract_address"),
                cst.parse_statement(
                    "self.contract = web3.eth.contract(address=self.address, abi=CONTRACT_ABI)"
                ),
            ]
        ),
        params=cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(
                    name=cst.Name("web3"),
                    annotation=cst.Annotation(annotation=cst.Name("Web3")),
                ),
                cst.Param(
                    name=cst.Name("contract_address"),
                    annotation=make_annotation(["Address", "ChecksumAddress"]),
                ),
            ]
        ),
    )
    class_functions = [class_constructor] + [
        generate_contract_function(function)
        for function in abi
        if function["type"] == "function"
    ]
    return cst.ClassDef(
        name=cst.Name(class_name), body=cst.IndentedBlock(body=class_functions)
    )


def generate_contract_function(
    func_object: Union[Dict[str, Any], int]
) -> cst.FunctionDef:

    default_param_name = "arg"
    default_counter = 1
    func_params = []
    func_params.append(cst.Param(name=cst.Name("self")))

    param_names = []
    for param in func_object["inputs"]:
        param_name = normalize_abi_name(param["name"])
        if param_name == "":
            param_name = f"{default_param_name}{default_counter}"
            default_counter += 1
        param_type = make_annotation(python_type(param["type"]))
        param_names.append(param_name)
        func_params.append(
            cst.Param(
                name=cst.Name(value=param_name),
                annotation=param_type,
            )
        )
    func_raw_name = normalize_abi_name(func_object["name"])
    func_name = cst.Name(func_raw_name)

    proxy_call_code = (
        f"return self.contract.functions.{func_raw_name}({','.join(param_names)})"
    )
    func_body = cst.IndentedBlock(body=[cst.parse_statement(proxy_call_code)])
    func_returns = cst.Annotation(annotation=cst.Name(value="ContractFunction"))

    return cst.FunctionDef(
        name=func_name,
        params=cst.Parameters(params=func_params),
        body=func_body,
        returns=func_returns,
    )


def copy_web3_util(dest_dir: str) -> None:
    dest_filepath = os.path.join(dest_dir, "web3_util.py")
    if os.path.isfile(dest_filepath):
        print(f"{dest_filepath} file already exists")
    web3_util_path = os.path.join(os.path.dirname(__file__), "web3_util.py")
    copyfile(web3_util_path, dest_filepath)


def create_init_py(dest_dir: str) -> None:
    dest_filepath = os.path.join(dest_dir, "__init__.py")
    if os.path.isfile(dest_filepath):
        print(f"{dest_filepath} file already exists")
    with open(dest_filepath, "w") as ofp:
        ofp.write("")


def generate_contract_file(abi: Dict[str, Any], output_path: str):
    contract_body = cst.Module(body=[generate_contract_class(abi)]).code

    content = REPORTER_FILE_TEMPLATE.format(
        contract_body=contract_body,
        centipede_version=CENTIPEDE_VERSION,
    )
    contract_file_path = os.path.join(output_path, "interface.py")
    with open(contract_file_path, "w") as ofp:
        ofp.write(content)

    JSON_FILE_PATH = os.path.join(output_path, "abi.json")
    with open(JSON_FILE_PATH, "w") as ofp:
        ofp.write(json.dumps(abi))
    copy_web3_util(output_path)
    create_init_py(output_path)


def generate_argument_parser_function(abi: Dict[str, Any]) -> cst.FunctionDef:
    def generate_function_subparser(
        function_abi: ABIFunction,
        description: str,
    ) -> List[cst.SimpleStatementLine]:
        function_name = normalize_abi_name(function_abi["name"])
        subparser_init = cst.parse_statement(
            f'{function_name} = call_subcommands.add_parser("{function_name}", description="{description}")'
        )
        argument_parsers = []
        # TODO(yhtiyar): Functions can have the same name, we will need to ressolve it
        default_arg_counter = 1
        for arg in function_abi["inputs"]:
            arg_name = normalize_abi_name(arg["name"])
            if arg_name == "":
                arg_name = f"arg{default_arg_counter}"
                default_arg_counter += 1
            argument_parsers.append(
                cst.parse_statement(
                    f'{function_name}.add_argument("{arg_name}", help="Type:{arg["type"]}")'
                )
            )

        return (
            [subparser_init]
            + argument_parsers
            + [
                cst.parse_statement(
                    f"populate_subparser_with_common_args({function_name})"
                ),
                cst.EmptyLine(),
            ]
        )

    parser_init = [
        cst.parse_statement(
            f'parser = argparse.ArgumentParser(description="Your smart contract cli")'
        ),
        cst.parse_statement(
            f'subcommands = parser.add_subparsers(dest="subcommand", required=True)'
        ),
        cst.parse_statement(
            f'call = subcommands.add_parser("call",description="Call smart contract function")'
        ),
        cst.parse_statement(
            f'call_subcommands = call.add_subparsers(dest="function_name", required=True)'
        ),
    ]

    function_abis = [item for item in abi if item["type"] == "function"]
    subparsers = []
    for function_abi in function_abis:
        subparsers.extend(generate_function_subparser(function_abi, "description"))

    return cst.FunctionDef(
        name=cst.Name("generate_argument_parser"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=parser_init + subparsers + [cst.parse_statement("return parser")]
        ),
        returns=cst.Annotation(
            annotation=cst.Attribute(
                value=cst.Name("argparse"), attr=cst.Name("ArgumentParser")
            )
        ),
    )


def generate_contract_cli_file(abi: Dict[str, Any], output_path: str):

    cli_body = cst.Module(body=[generate_argument_parser_function(abi)]).code

    content = CLI_FILE_TEMPLATE.format(
        cli_content=cli_body,
        centipede_version=CENTIPEDE_VERSION,
    )

    cli_file_path = os.path.join(output_path, "cli.py")
    with open(cli_file_path, "w") as ofp:
        ofp.write(content)

    JSON_FILE_PATH = os.path.join(output_path, "abi.json")
    with open(JSON_FILE_PATH, "w") as ofp:
        ofp.write(json.dumps(abi))

    copy_web3_util(output_path)
    create_init_py(output_path)
