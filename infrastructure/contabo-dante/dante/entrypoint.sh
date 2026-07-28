#!/bin/sh
set -eu
mkdir -p /etc/dante
[ -f /etc/dante/sockd.conf ] || cp /default/sockd.conf /etc/dante/sockd.conf
[ -f /etc/dante/sockd.passwd ] || touch /etc/dante/sockd.passwd
exec /usr/sbin/sockd -f /etc/dante/sockd.conf
