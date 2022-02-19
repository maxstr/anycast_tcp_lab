#!/bin/bash

set -eux

SOURCE_ADDRESS=$(ip -br a | grep 192.168.10 | awk '{print $3}'| cut -d '/' -f 1)
ROUTER_ADDRESS=$(dig +short router-internet)

ip route delete default || true
ip route add default via $ROUTER_ADDRESS dev eth1 src $SOURCE_ADDRESS

sleep infinity
