import json
from dataclasses import dataclass
from re import L

from moonstreamdb.db import yield_db_session_ctx
from moonstreamdb.models import PolygonLabel
from sqlalchemy.orm.session import Session
from web3 import Web3

from .contracts import CU

ADDRESS = "0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f"
MUMBAI_ADDRESS = "0xA993c4759B731f650dfA011765a6aedaC91a4a88"


def get_all_DNA_events(session: Session):
    labels = (
        session.query(PolygonLabel)
        .filter(PolygonLabel.label == "moonworm")
        .filter(PolygonLabel.address == ADDRESS)
        .filter(PolygonLabel.label_data["name"].astext == "DNAUpdated")
        .all()
    )
    max_token = -1
    token_ids = []
    for label in labels:
        token_ids.append(label.label_data["args"]["tokenId"])
        max_token = max(max_token, label.label_data["args"]["tokenId"])

    print(len(token_ids))
    return token_ids


def filter_ids(_id, labeled_ids):
    with open(f"unicorn-classes-{_id}.json", "r") as ifp:
        original_ids = json.load(ifp)

    token_ids = [item["tokenId"] for item in original_ids]
    result = []
    for token in token_ids:
        if token not in labeled_ids:
            result.append({"tokenId": token, "class": _id})

    with open(f"processes-{_id}.json", "w") as ofp:
        json.dump(result, ofp)


action_map = {
    0: "add",
    1: "replace",
    2: "remove",
}

cu_contract = Web3().eth.contract(abi=CU.abi())


def get_all_diamond_cuts(session: Session):
    labels = (
        session.query(PolygonLabel.label_data)
        .filter(PolygonLabel.label == "moonworm")
        .filter(PolygonLabel.address == ADDRESS)
        .filter(PolygonLabel.label_data["name"].astext == "diamondCut")
        .filter(PolygonLabel.label_data["status"].astext == "1")
        .order_by(PolygonLabel.block_number.asc())
        .all()
    )

    return labels


def get_function_name_by_selector(selector: str):
    try:

        name = cu_contract.get_function_by_selector(selector).function_identifier
        return name
    except Exception as e:
        print(e)
        print(selector)
        return "UNKNOWN"


def run():

    with yield_db_session_ctx() as session:
        diamond_cuts_events = get_all_diamond_cuts(session)

    selector_actions = {}
    current_index = 0
    for event in diamond_cuts_events:
        diamond_cuts = event[0]["args"]["_diamondCut"]
        for diamond_cut in diamond_cuts:
            for selector in diamond_cut[2]:
                if selector not in selector_actions:
                    selector_actions[selector] = []
                selector_actions[selector].append(
                    {
                        "name": get_function_name_by_selector(selector),
                        "action": action_map[diamond_cut[1]],
                        "address": diamond_cut[0],
                        "action_index": current_index,
                    }
                )
                current_index += 1

    current_cuts = {}
    for selector, actions in selector_actions.items():
        last_cut = None
        last_cut_index = -1
        for action in actions:
            if action["action_index"] > last_cut_index:
                last_cut_index = action["action_index"]
                if action["action"] == "remove":
                    last_cut = {"name": action["name"], "address": None}
                else:
                    last_cut = {"name": action["name"], "address": action["address"]}
        current_cuts[selector] = last_cut

    grouped_by_name = {}
    for selector, cut in current_cuts.items():
        if grouped_by_name.get(cut["name"]) is None:
            grouped_by_name[cut["name"]] = []
        grouped_by_name[cut["name"]].append(
            {"selector": selector, "address": cut["address"]}
        )

    with open("current_cuts.json", "w") as ofp:
        json.dump(grouped_by_name, ofp)


run()
