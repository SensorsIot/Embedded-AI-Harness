#!/bin/bash
# Notify the RFC2217 portal of a udev hotplug event.
# Called via systemd-run from 99-rfc2217-hotplug.rules.
#
# Args: ACTION DEVNAME ID_PATH DEVPATH

ACTION="$1"
DEVNAME="$2"
ID_PATH="$3"
DEVPATH="$4"

# Same port override the portal's unit reads; udev gives us none of its environment.
[ -r /etc/default/rfc2217-portal ] && . /etc/default/rfc2217-portal

curl -m 10 -s -X POST "http://127.0.0.1:${PORTAL_PORT:-8080}/api/hotplug" \
  -H 'Content-Type: application/json' \
  -d "{\"action\":\"$ACTION\",\"devnode\":\"$DEVNAME\",\"id_path\":\"${ID_PATH:-}\",\"devpath\":\"$DEVPATH\"}" \
  || true
