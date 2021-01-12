#!/bin/sh -eux

sed -i -e '/Defaults\s\+env_reset/a Defaults\texempt_group=sudo' /etc/sudoers;

# Set up password-less sudo for the user
echo '$SSH_USERNAME ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/99_$SSH_USERNAME;
chmod 440 /etc/sudoers.d/99_$SSH_USERNAME;