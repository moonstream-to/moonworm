import copy
import keyword
import logging
import os
from typing import Any, Dict, List, Set, Union, cast

import black
import black.mode
import inflection
import libcst as cst

from ..version import MOONWORM_VERSION

CONTRACT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "contract.py.template")
try:
    with open(CONTRACT_TEMPLATE_PATH, "r") as ifp:
        INTERFACE_FILE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(
        f"WARNING: Could not load contract template from {CONTRACT_TEMPLATE_PATH}:"
    )
    logging.warn(e)

CLI_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "cli.py.template")
try:
    with open(CLI_TEMPLATE_PATH, "r") as ifp:
        CLI_FILE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(f"WARNING: Could not load cli template from {CLI_TEMPLATE_PATH}:")
    logging.warn(e)


DEFAULT_CONSTRUCTOR = {
    "inputs": [],
    "stateMutability": "payable",
    "type": "constructor",
}


def get_constructor(abi: List[Dict[str, Any]]) -> Dict[str, Any]:
    for item in abi:
        if item["type"] == "constructor":
            return item
    return DEFAULT_CONSTRUCTOR


def format_code(code: str) -> str:
    formatted_code = black.format_str(code, mode=black.mode.Mode())
    return formatted_code


def make_annotation(types: list, optional: bool = False):
    annotation = cst.Annotation(annotation=cst.Name(types[0]))
    if len(types) > 1:
        union_slice = []
        for _type in types:
            union_slice.append(
                cst.SubscriptElement(
                    slice=cst.Index(
                        value=cst.Name(_type),
                    )
                ),
            )
        annotation = cst.Annotation(
            annotation=cst.Subscript(value=cst.Name("Union"), slice=union_slice)
        )

    if optional:
        annotation = cst.Annotation(
            annotation=cst.Subscript(
                value=cst.Name("Optional"),
                slice=[
                    cst.SubscriptElement(slice=cst.Index(value=annotation.annotation))
                ],
            )
        )

    return annotation


def normalize_abi_name(name: str) -> str:
    if keyword.iskeyword(name):
        return name + "_"
    else:
        return name


def python_type(evm_type: str) -> List[str]:
    if evm_type.endswith("]"):
        return ["List"]
    if evm_type.startswith(("uint", "int")):
        return ["int"]
    if evm_type.startswith(("int", "int")):
        return ["int"]
    elif evm_type.startswith("bytes"):
        return ["bytes"]
    elif evm_type == "string":
        return ["str"]
    elif evm_type == "address":
        return ["ChecksumAddress"]
    elif evm_type == "bool":
        return ["bool"]
    else:
        return ["Any"]


def generate_contract_class(
    abi: List[Dict[str, Any]],
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
                    annotation=make_annotation(["ChecksumAddress"]),
                ),
            ]
        ),
    )
    contract_constructors = [c for c in abi if c["type"] == "constructor"]
    if len(contract_constructors) == 1:
        contract_constructor = contract_constructors[0]
    elif len(contract_constructors) == 0:
        contract_constructor = {"inputs": []}
    else:
        raise ValueError("Multiple constructors found in ABI")

    contract_constructor["name"] = "constructor"
    class_functions = (
        [class_constructor]
        + [generate_contract_constructor_function(contract_constructor)]
        + [
            generate_contract_function(function)
            for function in abi
            if function["type"] == "function"
        ]
    )
    return cst.ClassDef(
        name=cst.Name(class_name), body=cst.IndentedBlock(body=class_functions)
    )


# This is a list of names that should be modified for smart contract arguments on the command line.
# We do this because smart contract argument names can sometimes collide with default arguments for
# transactions (see "generate_add_default_arguments" in brownie.py for an example of default arguments).
PROTECTED_ARG_NAMES: Set[str] = {
    "address",
    "chain",
    "confirmations",
    "gas-price",
    "gas-limit",
    "network",
    "nonce",
    "password",
    "sender",
    "signer",
}


def function_spec(function_abi: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Accepts function interface definitions from smart contract ABIs. An example input:
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_tokenId",
                "type": "uint256"
            }
        ],
        "name": "getDNA",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }

    Returns an dictionary of the form:
    {
        "abi": "getDNA",
        "method": "get_dna",
        "cli": "get-dna",
        "inputs": [
            {
                "abi": "_tokenId",
                "method": "_tokenId",
                "cli": "--token-id",
                "args": "token_id",
                "type": int,
                "cli_type": int,
            },
        ],
        "transact": False,
    }
    """
    abi_name = function_abi.get("name")
    if abi_name is None:
        raise ValueError('function_spec -- Valid function ABI must have a "name" field')

    underscored_name = inflection.underscore(abi_name)
    function_name = normalize_abi_name(underscored_name)
    cli_name = inflection.dasherize(underscored_name)

    default_input_name = "arg"
    default_counter = 1

    inputs: List[Dict[str, Any]] = []
    for item in function_abi.get("inputs", []):
        item_abi_name = item.get("name")
        if not item_abi_name:
            item_abi_name = f"{default_input_name}{default_counter}"
            default_counter += 1

        item_method_name = normalize_abi_name(inflection.underscore(item_abi_name))
        item_args_name = item_method_name
        if (
            item_args_name.startswith("_")
            or item_args_name.endswith("_")
            or item_args_name in PROTECTED_ARG_NAMES
        ):
            item_args_name = item_args_name.strip("_") + "_arg"

        item_cli_name = f"--{inflection.dasherize(item_args_name)}"

        item_type = python_type(item["type"])[0]

        item_cli_type = None
        if item_type in {"int", "str"}:
            item_cli_type = item_type

        input_spec: Dict[str, Any] = {
            "abi": item_abi_name,
            "method": item_method_name,
            "cli": item_cli_name,
            "args": item_args_name,
            "type": item_type,
            "raw_type": item["type"],
            "cli_type": item_cli_type,
        }

        inputs.append(input_spec)

    transact = True
    if function_abi.get("stateMutability") == "view":
        transact = False

    spec = {
        "abi": abi_name,
        "method": function_name,
        "cli": cli_name,
        "inputs": inputs,
        "transact": transact,
    }

    return spec


def generate_contract_constructor_function(
    func_object: Dict[str, Any]
) -> cst.FunctionDef:
    default_param_name = "arg"
    default_counter = 1
    func_params = []

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

    proxy_call_code = f"return ContractConstructor({','.join(param_names)})"
    func_body = cst.IndentedBlock(body=[cst.parse_statement(proxy_call_code)])
    func_returns = cst.Annotation(annotation=cst.Name(value="ContractConstructor"))

    return cst.FunctionDef(
        name=func_name,
        decorators=[cst.Decorator(decorator=cst.Name("staticmethod"))],
        params=cst.Parameters(params=func_params),
        body=func_body,
        returns=func_returns,
    )


def generate_contract_function(func_object: Dict[str, Any]) -> cst.FunctionDef:

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


def generate_argument_parser_function(abi: List[Dict[str, Any]]) -> cst.FunctionDef:
    def generate_function_subparser(
        function_abi: Dict[str, Any],
        description: str,
    ) -> List[Union[cst.SimpleStatementLine, cst.BaseCompoundStatement]]:
        function_name = normalize_abi_name(function_abi["name"])
        subparser_init = [
            cst.parse_statement(
                f'{function_name}_call = call_subcommands.add_parser("{function_name}", description="{description}")'
            ),
            cst.parse_statement(
                f'{function_name}_transact = transact_subcommands.add_parser("{function_name}", description="{description}")'
            ),
        ]
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
                    f'{function_name}_call.add_argument("{arg_name}", help="Type:{arg["type"]}")'
                )
            )
            argument_parsers.append(
                cst.parse_statement(
                    f'{function_name}_transact.add_argument("{arg_name}", help="Type:{arg["type"]}")'
                )
            )

        return (
            subparser_init
            + argument_parsers
            + [
                cst.parse_statement(
                    f"populate_subparser_with_common_args({function_name}_call)"
                ),
                cst.parse_statement(
                    f"populate_subparser_with_common_args({function_name}_transact)"
                ),
                cast(cst.SimpleStatementLine, cst.EmptyLine()),
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
        cst.parse_statement(
            f'transact = subcommands.add_parser("transact",description="Make transaction to smart contract function")'
        ),
        cst.parse_statement(
            f'transact_subcommands = transact.add_subparsers(dest="function_name", required=True)'
        ),
    ]

    function_abis = [item for item in abi if item["type"] == "function"]
    subparsers = []
    for function_abi in function_abis:
        subparsers.extend(generate_function_subparser(function_abi, "description"))

    # Deploy argparser:
    contract_constructors = [item for item in abi if item["type"] == "constructor"]
    if len(contract_constructors) == 1:
        contract_constructor = contract_constructors[0]
    elif len(contract_constructors) == 0:
        contract_constructor = {"inputs": []}
    else:
        raise Exception("Multiple constructors found")

    deploy_argument_parsers = []
    default_arg_counter = 1
    for arg in contract_constructor["inputs"]:
        arg_name = normalize_abi_name(arg["name"])
        if arg_name == "":
            arg_name = f"arg{default_arg_counter}"
            default_arg_counter += 1
        deploy_argument_parsers.append(
            cst.parse_statement(
                f'deploy.add_argument("{arg_name}", help="Type:{arg["type"]}")'
            )
        )
    deploy_parser = (
        [
            cst.parse_statement(
                'deploy = subcommands.add_parser("deploy", description="Deploy contract")'
            )
        ]
        + deploy_argument_parsers
        + [cst.parse_statement("populate_deploy_subparser(deploy)")]
    )
    return cst.FunctionDef(
        name=cst.Name("generate_argument_parser"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(
            body=parser_init
            + subparsers
            + deploy_parser
            + [cst.parse_statement("return parser")]
        ),
        returns=cst.Annotation(
            annotation=cst.Attribute(
                value=cst.Name("argparse"), attr=cst.Name("ArgumentParser")
            )
        ),
    )


def generate_contract_interface_content(
    abi: List[Dict[str, Any]], abi_file_name: str, format: bool = True
) -> str:
    contract_body = cst.Module(body=[generate_contract_class(abi)]).code

    content = INTERFACE_FILE_TEMPLATE.format(
        contract_body=contract_body,
        moonworm_version=MOONWORM_VERSION,
        abi_file_name=abi_file_name,
    )

    if format:
        content = format_code(content)

    return content


def generate_contract_cli_content(
    abi: List[Dict[str, Any]], abi_file_name: str, format: bool = True
) -> str:
    cli_body = cst.Module(body=[generate_argument_parser_function(abi)]).code

    content = CLI_FILE_TEMPLATE.format(
        cli_content=cli_body,
        moonworm_version=MOONWORM_VERSION,
        abi_file_name=abi_file_name,
    )

    if format:
        content = format_code(content)

    return content
