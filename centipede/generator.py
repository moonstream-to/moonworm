import json
import logging
import os
from typing import Any, Dict, Union

import libcst as cst
from eth_typing.evm import Address, ChecksumAddress
from libcst._nodes.statement import SimpleStatementLine
from libcst._parser.entrypoints import parse_statement

CONTRACT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "contract.py.template")
try:
    with open(CONTRACT_TEMPLATE_PATH, "r") as ifp:
        REPORTER_FILE_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(
        f"WARNING: Could not load reporter template from {CONTRACT_TEMPLATE_PATH}:"
    )
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


EVM_PYTHON_TYPE_MAPPINGS = {
    "uint256": make_annotation(["int"]),
    "uint8": make_annotation(["int"]),
    "uint": make_annotation(["int"]),
    "bytes4": make_annotation(["bytes"]),
    "string": make_annotation(["str"]),
    "address": make_annotation(["Address", "ChecksumAddress"]),
}


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
        param_name = param["name"]
        if param_name == "":
            param_name = f"{default_param_name}{default_counter}"
            default_counter += 1
        param_type = EVM_PYTHON_TYPE_MAPPINGS[param["type"]]
        param_names.append(param_name)
        func_params.append(
            cst.Param(
                name=cst.Name(value=param_name),
                annotation=param_type,
            )
        )

    func_name = cst.Name(func_object["name"])

    proxy_call_code = f"return self.contract.functions.{func_object['name']}({','.join(param_names)}).call()"
    func_body = cst.IndentedBlock(body=[cst.parse_statement(proxy_call_code)])
    func_returns = cst.Annotation(annotation=cst.Name(value="Any"))

    return cst.FunctionDef(
        name=func_name,
        params=cst.Parameters(params=func_params),
        body=func_body,
        returns=func_returns,
    )


def generate_contract_file(abi: Dict[str, Any], output_path: str):
    contract_body = cst.Module(body=[generate_contract_class(abi)]).code

    JSON_FILE_PATH = os.path.join(output_path, "abi.json")

    content = REPORTER_FILE_TEMPLATE.format(
        abi_json=JSON_FILE_PATH,
        contract_body=contract_body,
    )
    contract_file_path = os.path.join(output_path, "lol.py")
    with open(contract_file_path, "w") as ofp:
        ofp.write(content)

    with open(JSON_FILE_PATH, "w") as ofp:
        ofp.write(json.dumps(abi))
