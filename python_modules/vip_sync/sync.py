#!/usr/bin/env python3
import argparse
from typing import Set
import os.path

import yaml
import pyroute2

TABLE_ID = 200
BASE_RULE_PRIORITY = 9001
INTERFACES = ['eth0', 'eth1']

ndb = pyroute2.NDB(log='debug')

parser = argparse.ArgumentParser()
parser.add_argument("service_file")

args = parser.parse_args()

with open(os.path.expanduser(args.service_file), 'r') as fh:
    loaded = yaml.safe_load(fh)

# Ensure rule exists
for index, interface in enumerate(sorted(INTERFACES)):
    expected_rule = {'table': TABLE_ID, 'priority': BASE_RULE_PRIORITY + index, 'iifname': interface}
    try:
        rule = ndb.rules[expected_rule]
    except KeyError:
        # Need to create it
        ndb.rules.create(**expected_rule).commit()

expected_vips: Set[str] = set()
for virtual_ip, info in loaded['vips'].items():
    expected_vips.add(virtual_ip)

expected_route_prefixes = set(map(lambda vip: f"{vip}/32", expected_vips))


def route_dict(vip: str):
    return {"table": TABLE_ID,
            "dst": vip,
            # lo
            "oif": 1,
            "scope": 254,
            # This is a local route type
            "type": 2}


existing_route_prefixes = set()
for route in ndb.routes.dump().filter(table=TABLE_ID).select("dst", "dst_len"):
    existing_route_prefixes.add(f"{route.dst}/{route.dst_len}")

for to_delete in existing_route_prefixes - expected_route_prefixes:
    ndb.routes[{'dst': to_delete, 'table': TABLE_ID}].remove().commit()

for to_add in expected_route_prefixes - existing_route_prefixes:
    ndb.routes.create(**route_dict(to_add)).commit()
