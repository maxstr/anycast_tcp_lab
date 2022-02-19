#!/bin/sh

ip link add dev tunl0 type ipip || true
ip link set up tunl0
python3 /opt/nftables_sync/__main__.py /services.yaml
