import enum
from typing import Dict, List


class NFTableHook(enum.Enum):
    PREROUTING = "prerouting"
    OUTPUT = "output"

def create_table(table_name: str) -> Dict:
    return {"nftables": [{"add": {"table": {"family": "ip", "name": table_name}}}]}

def create_chain(table_name: str, chain_name: str, hook: NFTableHook) -> Dict:
    return {"nftables": [
        {"add":
             {"chain":
                  {"family": "ip", "name": chain_name, "table": table_name, "type": "nat", "prio": -100, "hook": hook.value}
              }
         }]
    }

def create_map(table_name: str, map_name: str) -> Dict:
    return {"nftables": [
        {"add":
            {"map": {
                "family": "ip",
                "table": table_name,
                "name": map_name,
                "type": ["ipv4_addr", "inet_service"],
                "map": "inet_service",
            }}}
    ]}

def dnat_to_localhost_expression(map_name: str) -> List[Dict]:
    """
    Command for creating a list of expressions that will match virtual_ip, virtual_port into a map
    :return: List of expressions
    """
    # A TCP match is required in order to map dport in the second expression
    tcp_match = {'match': {'left': {'meta': {'key': 'l4proto'}},
                           'right': 'tcp',
                           'op': '=='
                           }
                 }

    dnat_option = {"dnat": {
        'addr': '127.0.0.1',
        'port': {"map": {'data': f'@{map_name}',
                         'key': {'concat': [{'payload': {'field': 'daddr',
                                                         'protocol': 'ip'}},
                                            {'payload': {'field': 'dport',
                                                         'protocol': 'tcp'}}]}}},
        }
    }
    return [tcp_match, dnat_option]

def read_map(table_name: str, map_name: str) -> Dict:
    return {'nftables': [
        {"list": {"map": {"family": "ip", "name": map_name, "table": table_name}}}
    ]}

def read_rules_in_chain(table_name: str, chain: str) -> Dict:
    return {'nftables': [
        {"list": {"chain": {"family": "ip", "table": table_name, "name": chain}}}
    ]}

def create_rule(table_name: str, chain: str, expressions: List[Dict]) -> Dict:
    return {"nftables": [
        {"add":
            {"rule": {
                "family": "ip",
                "table": table_name,
                "chain": chain,
                "expr": expressions,
            }}}
    ]}