#!/bin/bash
# ==============================================================================
# SDC Pilot: Optional Direct Standalone Hotspot Setup for Raspberry Pi 5
# Configures hostapd & dnsmasq for school labs where no external router is available.
# SSID: Sindhi_Digital_Classroom | Static IP: 192.168.4.1
# ==============================================================================

set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo bash deploy/setup_offline_hotspot.sh"
  exit 1
fi

echo "=========================================================="
echo " Configuring Standalone Wi-Fi Hotspot on Raspberry Pi 5"
echo " Network SSID: Sindhi_Digital_Classroom"
echo " Local Gateway IP: 192.168.4.1"
echo "=========================================================="

# 1. Install networking tools
apt-get update
apt-get install -y hostapd dnsmasq iptables rfkill

# 2. Unblock Wi-Fi
rfkill unblock wlan || true

# 3. Configure static IP for wlan0
cat << 'EOF' > /etc/network/interfaces.d/wlan0
allow-hotplug wlan0
iface wlan0 inet static
    address 192.168.4.1
    netmask 255.255.255.0
EOF

# 4. Configure dnsmasq (DHCP server for Android clients)
systemctl stop dnsmasq || true
cat << 'EOF' > /etc/dnsmasq.d/sdc-hotspot.conf
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.200,255.255.255.0,24h
domain=sdc.local
address=/sdc.classroom/192.168.4.1
address=/classroom.local/192.168.4.1
EOF

# 5. Configure hostapd (Wi-Fi Access Point)
systemctl stop hostapd || true
cat << 'EOF' > /etc/hostapd/hostapd.conf
country_code=PK
interface=wlan0
ssid=Sindhi_Digital_Classroom
hw_mode=g
channel=7
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=sindhiclassroom
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|g' /etc/default/hostapd || true

# 6. Enable and restart services
systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq

systemctl restart hostapd
systemctl restart dnsmasq

echo "=========================================================="
echo " Standalone Hotspot Active!"
echo " SSID: Sindhi_Digital_Classroom (Password: sindhiclassroom)"
echo " Classroom URL: http://192.168.4.1:8000/classroom"
echo "=========================================================="
