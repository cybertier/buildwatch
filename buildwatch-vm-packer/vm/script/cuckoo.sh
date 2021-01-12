#!/bin/sh -eux

# This file is based on cuckoo 2.0.7
# https://cuckoo.sh/docs/installation/guest/linux.html#preparing-x32-x64-ubuntu-18-04-linux-guests
INSTALL_DIR="/root/.cuckoo"
AGENT_NAME="obfucated"


# install dependencies 
export DEBIAN_FRONTEND=noninteractive
apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C8CAB6595FDFF622
codename=$(lsb_release -cs)
tee /etc/apt/sources.list.d/ddebs.list << EOF
  deb http://ddebs.ubuntu.com/ ${codename}          main restricted universe multiverse
  #deb http://ddebs.ubuntu.com/ ${codename}-security main restricted universe multiverse
  deb http://ddebs.ubuntu.com/ ${codename}-updates  main restricted universe multiverse
  deb http://ddebs.ubuntu.com/ ${codename}-proposed main restricted universe multiverse
EOF
apt-get -y update
apt-get -y install \
    linux-image-$(uname -r)-dbgsym \
    systemtap \
    gcc \
    patch \
    linux-headers-$(uname -r)\
    python2.7

cd /root

# Patch the SystemTap tapset, so that the Cuckoo analyzer can properly parse the output:
wget https://raw.githubusercontent.com/cuckoosandbox/cuckoo/master/stuff/systemtap/expand_execve_envp.patch
wget https://raw.githubusercontent.com/cuckoosandbox/cuckoo/master/stuff/systemtap/escape_delimiters.patch
patch /usr/share/systemtap/tapset/linux/sysc_execve.stp < expand_execve_envp.patch
patch /usr/share/systemtap/tapset/uconversions.stp < escape_delimiters.patch

# Compile the kernel extension:
wget https://raw.githubusercontent.com/axel1200/cuckoo/master/stuff/systemtap/strace.stp
stap -p4 -r $(uname -r) strace.stp -m stap_ -v -g

#  You will now be able to test the STAP kernel extension as follows:
# However, this call does not return, so we skip it.
# staprun -v ./stap_.ko | grep "Module stap_ inserted"


# The extension needs to be placed here. I don't know why
mkdir -p $INSTALL_DIR
mv stap_.ko $INSTALL_DIR

# copy the agent
cd $INSTALL_DIR
wget https://raw.githubusercontent.com/cuckoosandbox/cuckoo/master/cuckoo/data/agent/agent.py
mv agent.py $AGENT_NAME

# ensure the agent autostarts
(crontab -l || true; echo "@reboot python2.7 $INSTALL_DIR/$AGENT_NAME")| crontab -

# disable the firewall
ufw disable

# diable ntp (i guess that might be handled by the agent)
timedatectl set-ntp off

# remove packages that may cause noise
apt-get -y purge \
    update-notifier \
    update-manager \
    update-manager-core \
    ubuntu-release-upgrader-core \
    whoopsie \
    ntpdate \
    cups-daemon \
    avahi-autoipd \
    avahi-daemon \
    avahi-utils \
    account-plugin-salut \
    libnss-mdns \
    telepathy-salut
