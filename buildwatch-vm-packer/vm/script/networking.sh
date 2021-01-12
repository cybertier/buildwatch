#!/bin/sh -eux

echo "Create netplan config for eth0"
rm -rf /etc/netplan/01-netcfg.yaml
if [[ -z "${static_ip}" ]]
then
  cat <<EOF >/etc/netplan/01-netcfg.yaml;
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
EOF
else
  cat >> /etc/netplan/01-netcfg.yaml <<EOL
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      dhcp6: no
      addresses: [$static_ip/24]
      gateway4: 192.168.56.1
      nameservers:
        addresses: [1.1.1.1,8.8.8.8]
EOL
fi 

# Disable Predictable Network Interface names and use eth0
sed -i 's/en[[:alnum:]]*/eth0/g' /etc/network/interfaces;
sed -i 's/GRUB_CMDLINE_LINUX="\(.*\)"/GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0 \1"/g' /etc/default/grub;
update-grub;
