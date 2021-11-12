import keyword
import logging
import os
from typing import Any, Dict, List, Union, cast

import libcst as cst
from libcst._nodes.statement import BaseCompoundStatement
from web3.types import ABIFunction

from .version import MOONWORM_VERSION

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
        return ["ChecksumAddress"]
    elif evm_type == "bool":
        return ["bool"]
    elif evm_type == "tuple[]":
        return ["list"]
    else:
        raise ValueError(f"Cannot convert to python type {evm_type}")


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
    abi: List[Dict[str, Any]], abi_file_name: str
) -> str:
    contract_body = cst.Module(body=[generate_contract_class(abi)]).code

    content = INTERFACE_FILE_TEMPLATE.format(
        contract_body=contract_body,
        moonworm_version=MOONWORM_VERSION,
        abi_file_name=abi_file_name,
    )
    return content


def generate_contract_cli_content(abi: List[Dict[str, Any]], abi_file_name: str) -> str:

    cli_body = cst.Module(body=[generate_argument_parser_function(abi)]).code

    content = CLI_FILE_TEMPLATE.format(
        cli_content=cli_body,
        moonworm_version=MOONWORM_VERSION,
        abi_file_name=abi_file_name,
    )

    return content
