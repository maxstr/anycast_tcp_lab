from functools import wraps
from typing import Tuple, Set, Mapping, Dict, List
from pprint import pprint
import nftables
import nftables_commands

TABLE_NAME_PREFIX = 'moltar'
TABLE_NAME = f'__{TABLE_NAME_PREFIX}_nat'
PREROUTING_CHAIN_NAME = 'PREROUTING'
OUTPUT_CHAIN_NAME = 'OUTPUT'
NAT_MAP_NAME = 'vip_nat'
_NFT_CLIENT = None
_INITIALIZED = False

def rules_are_same(to_add: Dict, from_nft: Dict):
    if to_add == from_nft:
        return True
    if not isinstance(to_add, dict) or not isinstance(from_nft, dict):
        return False
    for key, value in to_add.items():
        if key not in from_nft or not rules_are_same(value, from_nft[key]):
            return False
    return True

def _get_client():
    global _NFT_CLIENT
    if _NFT_CLIENT:
        return _NFT_CLIENT
    client = nftables.Nftables()
    #old_func = client.json_cmd
    #@wraps(client.json_cmd)
    #def _new_cmd(cmd):
    #    pprint(cmd)
    #    result = old_func(cmd)
    #    pprint(result)
    #    assert result[0] == 0
    #    return result
    #setattr(client, 'json_cmd', _new_cmd)

    _NFT_CLIENT = client
    return client

def setup_infra():
    global _INITIALIZED
    nft = _get_client()
    nft.json_cmd(nftables_commands.create_table(TABLE_NAME))
    nft.json_cmd(nftables_commands.create_map(TABLE_NAME, NAT_MAP_NAME))

    # Create PREROUTING chain
    nft.json_cmd(nftables_commands.create_chain(TABLE_NAME, PREROUTING_CHAIN_NAME, nftables_commands.NFTableHook.PREROUTING))

    existing_prerouting_rules = get_existing_rules_in_chain(PREROUTING_CHAIN_NAME)
    prerouting_rule_add = nftables_commands.create_rule(TABLE_NAME, PREROUTING_CHAIN_NAME, nftables_commands.dnat_to_localhost_expression(NAT_MAP_NAME))
    if not any(map(lambda existing_rule: rules_are_same(prerouting_rule_add['nftables'][0]['add'], existing_rule), existing_prerouting_rules)):
        nft.json_cmd(prerouting_rule_add)

    # Create OUTPUT chain
    nft.json_cmd(nftables_commands.create_chain(TABLE_NAME, OUTPUT_CHAIN_NAME, nftables_commands.NFTableHook.OUTPUT))
    existing_output_rules = get_existing_rules_in_chain(OUTPUT_CHAIN_NAME)
    output_rule_add = nftables_commands.create_rule(TABLE_NAME, OUTPUT_CHAIN_NAME, nftables_commands.dnat_to_localhost_expression(NAT_MAP_NAME))
    print(output_rule_add)
    if not any(map(lambda existing_rule: rules_are_same(output_rule_add['nftables'][0]['add'], existing_rule), existing_output_rules)):
        nft.json_cmd(output_rule_add)

    _INITIALIZED = True

def get_existing_rules_in_chain(chain: str) -> List[Dict]:
    client = _get_client()
    rc, get_output, _ = client.json_cmd(nftables_commands.read_rules_in_chain(TABLE_NAME, chain))
    rules = list(filter(lambda output: bool(output.get('rule')), get_output['nftables']))
    return rules

def get_existing_nats() -> Set[Tuple[str, int, int]]:
    assert _INITIALIZED
    client = _get_client()
    # Get current NATs
    get_command = {"nftables": [{"list": {"map": {"family": "ip", "name": NAT_MAP_NAME, "table": TABLE_NAME}}}]}
    rc, get_output, _ = client.json_cmd(nftables_commands.read_map(TABLE_NAME, NAT_MAP_NAME))
    # ensure only a single map
    maps = list(filter(lambda a: bool(a.get('map')), get_output['nftables']))
    assert len(maps) == 1
    map_ = maps[0]
    current_nats: Set[Tuple[str, int, int]] = set()
    for elem in map_['map'].get('elem', []):
        concat, real_port = elem
        virtual_ip, virtual_port = concat['concat']
        current_nats.add((virtual_ip, virtual_port, real_port))
    return current_nats


def sync_to_local(expected_nats: Set[Tuple[str, int, int]]):
    assert _INITIALIZED
    client = _get_client()
    current_nats = get_existing_nats()

    to_delete = current_nats - expected_nats
    to_add = expected_nats - current_nats

    for virtual_ip, virtual_port, real_port in to_delete:
        delete_set_command = {"nftables":[
            {"delete": {
                "element": {
                    "family": "ip",
                    "table": TABLE_NAME,
                    "name": NAT_MAP_NAME,
                    "elem": [[{"concat": [virtual_ip, virtual_port]}, real_port]]
                }}}
        ]}
        client.json_cmd(delete_set_command)
    for virtual_ip, virtual_port, real_port in to_add:
        add_set_command = {
            "nftables": [
                {"add":
                    {"element": {
                        "family": "ip",
                        "table": TABLE_NAME,
                        "name": NAT_MAP_NAME,
                        "elem": [[{"concat": [virtual_ip, virtual_port]}, real_port]]
                        }
                    }
                },
            ]
        }
        client.json_cmd(add_set_command)

