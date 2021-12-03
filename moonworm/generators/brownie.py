import logging
import os
from typing import Any, Dict, List, Optional

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


def generate_get_transaction_config() -> cst.FunctionDef:
    function_body = cst.IndentedBlock(
        body=[
            cst.parse_statement("network.connect(args.network)"),
            cst.parse_statement(
                "signer = network.accounts.load(args.sender, args.password)"
            ),
            cst.parse_statement(
                'transaction_config: Dict[str, Any] = {"from": signer}'
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="gas_price"), value=cst.Name(value="args")
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["gas_price"] = args.gas_price'
                ),
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="confirmations"),
                        value=cst.Name(value="args"),
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["required_confs"] = args.confirmations'
                ),
            ),
            cst.parse_statement("return transaction_config"),
        ],
    )
    function_def = cst.FunctionDef(
        name=cst.Name(value="get_transaction_config"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(
            annotation=cst.Subscript(
                value=cst.Name(value="Dict"),
                slice=[
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name(value="str"))),
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name(value="Any"))),
                ],
            )
        ),
    )
    return function_def


def generate_cli_handler(
    function_abi: Dict[str, Any], contract_name: str
) -> Optional[cst.FunctionDef]:
    """
    Generates a handler which translates parsed command line arguments to method calls on the generated
    smart contract interface.

    Returns None if it is not appropriate for the given function to have a handler (e.g. fallback or
    receive). constructor is handled separately with a deploy handler.
    """
    function_name = function_abi.get("name")
    if function_name is None:
        return None

    function_body_raw: List[cst.CSTNode] = []

    requires_transaction = True
    if function_abi["stateMutability"] == "view":
        requires_transaction = False

    if requires_transaction:
        function_body_raw.append(
            cst.parse_statement("transaction_config = get_transaction_config(args)")
        )
    function_body_raw.append(cst.parse_statement("pass"))

    function_body = cst.IndentedBlock(body=function_body_raw)

    function_def = cst.FunctionDef(
        name=cst.Name(value=f"handle_{function_name}"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_brownie_cli(
    abi: List[Dict[str, Any]], contract_name: str
) -> List[cst.FunctionDef]:
    """
    Generates an argparse CLI to a brownie smart contract using the generated smart contract interface.
    """
    get_transaction_config_function = generate_get_transaction_config()
    handlers = [get_transaction_config_function]
    handlers.extend(
        [
            generate_cli_handler(function_abi, contract_name)
            for function_abi in abi
            if function_abi.get("type") == "function"
            and function_abi.get("name") is not None
        ]
    )
    nodes: List[cst.CSTNode] = [handler for handler in handlers if handler is not None]
    return nodes


def generate_brownie_interface(
    abi: List[Dict[str, Any]], contract_name: str, cli: bool = True, format: bool = True
) -> str:
    contract_class = generate_brownie_contract_class(abi, contract_name)
    module_body = [contract_class]

    if cli:
        contract_cli_functions = generate_brownie_cli(abi, contract_name)
        module_body.extend(contract_cli_functions)

    contract_body = cst.Module(body=module_body).code

    content = BROWNIE_INTERFACE_TEMPLATE.format(
        contract_body=contract_body,
        moonworm_version=MOONWORM_VERSION,
    )

    if format:
        content = format_code(content)

    return content
