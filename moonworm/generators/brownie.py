import logging
import os
from typing import Any, Dict, List

import libcst as cst

from ..version import MOONWORM_VERSION
from .basic import format_code, make_annotation, normalize_abi_name, python_type

BROWNIE_INTERFACE_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "brownie_contract.py.template"
)
try:
    with open(BROWNIE_INTERFACE_TEMPLATE_PATH, "r") as ifp:
        BROWNIE_INTERFACE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(
        f"WARNING: Could not load cli template from {BROWNIE_INTERFACE_TEMPLATE_PATH}:"
    )
    logging.warn(e)


def generate_brownie_contract_class(
    abi: List[Dict[str, Any]],
    contract_name: str,
) -> cst.ClassDef:
    class_name = contract_name
    class_constructor = cst.FunctionDef(
        name=cst.Name("__init__"),
        body=cst.IndentedBlock(
            body=[
                cst.parse_statement("self.address = contract_address"),
                cst.parse_statement(
                    f"self.contract = contract_from_build({contract_name})"
                ),
            ]
        ),
        params=cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(
                    name=cst.Name("contract_address"),
                    annotation=make_annotation(["ChecksumAddress"], optional=True),
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
        + [generate_brownie_constructor_function(contract_constructor)]
        + [
            generate_brownie_contract_function(function)
            for function in abi
            if function["type"] == "function"
        ]
    )
    return cst.ClassDef(
        name=cst.Name(class_name), body=cst.IndentedBlock(body=class_functions)
    )


def generate_brownie_constructor_function(
    func_object: Dict[str, Any]
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
    func_params.append(cst.Param(name=cst.Name("signer")))

    func_name = "deploy"
    param_names.append("{'from': signer}")
    proxy_call_code = (
        f"deployed_contract = self.contract.deploy({','.join(param_names)})"
    )

    func_body = cst.IndentedBlock(
        body=[
            cst.parse_statement(proxy_call_code),
            cst.parse_statement("self.address=deployed_contract.address"),
        ]
    )

    return cst.FunctionDef(
        name=cst.Name(func_name),
        params=cst.Parameters(params=func_params),
        body=func_body,
    )


def generate_brownie_contract_function(func_object: Dict[str, Any]) -> cst.FunctionDef:

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
    if func_object["stateMutability"] == "view":
        proxy_call_code = (
            f"return self.contract.{func_raw_name}.call({','.join(param_names)})"
        )
    else:
        func_params.append(cst.Param(name=cst.Name(value="signer")))
        param_names.append(f"{{'from': signer}}")
        proxy_call_code = (
            f"return self.contract.{func_raw_name}({','.join(param_names)})"
        )
    func_body = cst.IndentedBlock(body=[cst.parse_statement(proxy_call_code)])
    func_returns = cst.Annotation(annotation=cst.Name(value="Any"))

    return cst.FunctionDef(
        name=func_name,
        params=cst.Parameters(params=func_params),
        body=func_body,
        returns=func_returns,
    )


def generate_brownie_interface(
    abi: List[Dict[str, Any]], contract_name: str, format: bool = True
) -> str:
    contract_body = cst.Module(
        body=[generate_brownie_contract_class(abi, contract_name)]
    ).code

    content = BROWNIE_INTERFACE_TEMPLATE.format(
        contract_body=contract_body,
        moonworm_version=MOONWORM_VERSION,
    )

    if format:
        content = format_code(content)

    return content
