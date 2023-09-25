#!/bin/bash

# Enabling automatic security updates
apt-get install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades -y

# Removing unnecessary packages and services
apt-get remove -y telnet
apt-get remove -y rsh-server
apt-get remove -y rsh-client
apt-get remove -y xinetd
apt-get remove -y tftp
apt-get remove -y tftpd
apt-get remove -y talk
apt-get remove -y talkd

# Removing old software packages and clean up the package cache
apt-get autoremove -y
apt-get clean -y
