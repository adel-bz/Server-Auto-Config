#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

# Enabling automatic security updates
apt-get install -y unattended-upgrades
echo 'unattended-upgrades unattended-upgrades/enable_auto_updates boolean true' | debconf-set-selections
dpkg-reconfigure -f noninteractive unattended-upgrades

# Removing unnecessary packages and services
apt-get remove -y telnet || true
apt-get remove -y rsh-server || true
apt-get remove -y rsh-client || true
apt-get remove -y xinetd || true
apt-get remove -y tftp || true
apt-get remove -y tftpd || true
apt-get remove -y talk || true
apt-get remove -y talkd || true

# Removing old software packages and clean up the package cache
apt-get autoremove -y
apt-get clean -y
