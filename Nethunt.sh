#!/data/data/com.termux/files/usr/bin/bash
#
###############################################################################
#  Termux Hotspot Monitor — device scanner + DNS / HTTP sniffer
#  Author:  HackerAI
#  Purpose: Monitor devices connecting to your personal hotspot and see
#           what they're doing (DNS queries, HTTP requests, app activity).
#  Requires: tsu (root) OR PCAPdroid (no root) + tcpdump + termux-api
#
#  Installation:
#    pkg update && pkg upgrade
#    pkg install tsu tcpdump termux-api nmap iproute2
#
#  For non‑root devices, also install PCAPdroid from F‑Droid / Play Store.
###############################################################################

set -e

# ─── Colour output ───────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ─── Banner ──────────────────────────────────────────────────────────────────
banner() {
    clear
    echo -e "${RED}"
    echo "  ╔══════════════════════════════════════════════════════════╗"
    echo "  ║        🔥  TERMUX HOTSPOT SNIFFER v1.0  🔥             ║"
    echo "  ║     See who's on your hotspot & what they're doing      ║"
    echo "  ╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ─── Prerequisites check ────────────────────────────────────────────────────
check_deps() {
    local missing=""
    for cmd in tcpdump ip nmap; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=" $cmd"
        fi
    done
    if [ -n "$missing" ]; then
        echo -e "${YELLOW}[!] Missing packages:$missing${NC}"
        echo -e "${YELLOW}[!] Run: pkg install tsu tcpdump nmap termux-api${NC}"
        echo -e "${YELLOW}[!] Then re-run this script.${NC}"
        exit 1
    fi
    # Check root
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${YELLOW}[!] Not running as root. Packet capture limited.${NC}"
        echo -e "${YELLOW}[!] Recommend: tsu ./$(basename "$0")${NC}"
        echo ""
        HAS_ROOT=0
    else
        HAS_ROOT=1
    fi
}

# ─── Auto-detect hotspot interface ──────────────────────────────────────────
find_iface() {
    # Typical hotspot interfaces: ap0, wlan0, p2p-p2p0-*
    for iface in $(ip link | grep -oP '^\d+:\s+\K[^:@]+'); do
        state=$(ip link show "$iface" 2>/dev/null | grep -o 'state [A-Z]*' | cut -d' ' -f2)
        addr=$(ip addr show "$iface" 2>/dev/null | grep 'inet ' | awk '{print $2}')
        if [ "$state" = "UP" ] && [ -n "$addr" ]; then
            # Check if it's in a private range (hotspot)
            if echo "$addr" | grep -qE '^(192\.168\.|10\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[0-1]\.)'; then
                HOTSPOT_IFACE="$iface"
                HOTSPOT_NET="$addr"
                return 0
            fi
        fi
    done
    # Fallback: use the interface with the default route
    HOTSPOT_IFACE=$(ip route | grep default | head -1 | awk '{print $5}')
    if [ -z "$HOTSPOT_IFACE" ]; then
        echo -e "${RED}[!] Could not detect hotspot interface.${NC}"
        echo -e "${YELLOW}[!] Please set HOTSPOT_IFACE manually in the script.${NC}"
        exit 1
    fi
    HOTSPOT_NET=$(ip addr show "$HOTSPOT_IFACE" | grep 'inet ' | awk '{print $2}' | head -1)
    echo -e "${YELLOW}[*] Using fallback interface: $HOTSPOT_IFACE${NC}"
}

# ─── Resolve MAC vendor ──────────────────────────────────────────────────────
vendor_from_mac() {
    local mac="$1"
    local oui
    oui=$(echo "$mac" | tr '[:lower:]' '[:upper:]' | sed 's/[^A-F0-9]//g' | cut -c1-6)
    # Quick static lookup for common vendors
    case "$oui" in
        "00037F") echo "Apple" ;;
        "0016CB") echo "Apple" ;;
        "0017F2") echo "Apple" ;;
        "0025BC") echo "Apple" ;;
        "049226") echo "Samsung" ;;
        "08F9E0") echo "Samsung" ;;
        "0C68D8") echo "Samsung" ;;
        "100D7F") echo "Xiaomi" ;;
        "181414") echo "Xiaomi" ;;
        "28D1E6") echo "Xiaomi" ;;
        "0011FF") echo "Huawei" ;;
        "0881F4") echo "Huawei" ;;
        "78452F") echo "Huawei" ;;
        "34A395") echo "OnePlus" ;;
        "04829F") echo "OnePlus" ;;
        "A886DD") echo "Google" ;;
        "8C9350") echo "Google" ;;
        "001D0F") echo "Intel" ;;
        "3C970E") echo "Intel" ;;
        "B8AEED") echo "Microsoft" ;;
        "001D4F") echo "Sony" ;;
        "0475C8") echo "LG" ;;
        "E83EF9") echo "Nokia" ;;
        "AC3C0B") echo "HMD/Nokia" ;;
        "B8A9E0") echo "Raspberry Pi" ;;
        "DCA632") echo "Raspberry Pi" ;;
        *) echo "Unknown ($oui)" ;;
    esac
}

# ─── Refresh connected devices ──────────────────────────────────────────────
scan_devices() {
    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  📡  Scanning hotspot for connected devices...               │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}"

    local subnet
    subnet=$(echo "$HOTSPOT_NET" | cut -d'/' -f1 | awk -F. '{print $1"."$2"."$3".0/24"}')

    echo -e "${YELLOW}[*] Interface: $HOTSPOT_IFACE  |  Subnet: $subnet${NC}\n"

    # ARP scan using nmap (works without root)
    DEVICE_LIST=$(nmap -sn -n "$subnet" --exclude "$(echo "$HOTSPOT_NET" | cut -d'/' -f1)" 2>/dev/null | \
                  grep -E 'Nmap scan report for|MAC Address' | \
                  paste - - | \
                  sed 's/Nmap scan report for /IP: /;s/.*MAC Address: /| MAC: /')

    # Also try ip neigh for current ARP cache
    ARP_LIST=$(ip neigh | grep -v "$HOTSPOT_IFACE" | grep -E 'REACHABLE|STALE|DELAY' | \
               awk '{print "IP: " $1 " | MAC: " $5}')

    if [ -z "$DEVICE_LIST" ] && [ -z "$ARP_LIST" ]; then
        echo -e "${RED}  ⚠  No devices detected. Is your hotspot on and connected?${NC}"
        return
    fi

    # Deduplicate and print
    echo -e "${BOLD}${GREEN}  Connected Devices:${NC}"
    echo "  ───────────────────────────────────────────────────────"
    
    # Parse nmap output
    echo "$DEVICE_LIST" | while IFS= read -r line; do
        ip=$(echo "$line" | grep -oP 'IP: \K[0-9.]+')
        mac=$(echo "$line" | grep -oP 'MAC: [0-9A-Fa-f:]+')
        mac_clean=$(echo "$mac" | sed 's/MAC: //')
        vendor=$(vendor_from_mac "$mac_clean")
        echo -e "  ${GREEN}►${NC} $ip  │  $mac  │  ${YELLOW}$vendor${NC}"
    done

    # If nmap didn't work, show ARP table
    if [ -z "$DEVICE_LIST" ]; then
        echo "$ARP_LIST" | while IFS= read -r line; do
            ip=$(echo "$line" | grep -oP 'IP: \K[0-9.]+')
            mac=$(echo "$line" | grep -oP 'MAC: [0-9A-Fa-f:]+')
            mac_clean=$(echo "$mac" | sed 's/MAC: //')
            vendor=$(vendor_from_mac "$mac_clean")
            echo -e "  ${GREEN}►${NC} $ip  │  $mac  │  ${YELLOW}$vendor${NC}"
        done
    fi
    echo ""
}

# ─── Live DNS sniffer ───────────────────────────────────────────────────────
dns_sniff() {
    local outfile="hotspot_sniff_$(date +%Y%m%d_%H%M%S).log"
    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  🔍  LIVE DNS QUERY SNIFFER (port 53)                      │${NC}"
    echo -e "${CYAN}│     Shows domains each device is resolving                  │${NC}"
    echo -e "${CYAN}│     Press CTRL+C to stop                                    │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}\n"

    echo -e "${YELLOW}[*] Logging to: $outfile${NC}\n"

    if [ "$HAS_ROOT" -eq 1 ]; then
        # Full DNS capture with human-readable output
        tcpdump -i "$HOTSPOT_IFACE" -tnl -s0 port 53 2>/dev/null | \
        while IFS= read -r packet; do
            timestamp=$(date '+%H:%M:%S')
            # Extract IPs and query domain
            src=$(echo "$packet" | grep -oP '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
            dst=$(echo "$packet" | grep -oP '> [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sed 's/> //')
            domain=$(echo "$packet" | grep -oP '(A\?|AAAA\?|MX\?|TXT\?)\s+\K[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' | head -1)
            qtype=$(echo "$packet" | grep -oP '(A\?|AAAA\?|MX\?|TXT\?|CNAME\?|NS\?)')

            if [ -n "$domain" ]; then
                echo -e "[${timestamp}] ${GREEN}${src}${NC} → ${CYAN}${domain}${NC} (${qtype:-QUERY})" | \
                    tee -a "$outfile"
            fi
        done
    else
        # Non-root: limited to local DNS (runs over loopback)
        echo -e "${YELLOW}[!] No root — capturing DNS from localhost only.${NC}"
        echo -e "${YELLOW}[!] For full capture, run: tsu ./$(basename "$0")${NC}\n"
        echo -e "${YELLOW}[*] OR install PCAPdroid and redirect pcap to Termux.${NC}\n"
        sleep 2
    fi
}

# ─── Live HTTP sniffer ──────────────────────────────────────────────────────
http_sniff() {
    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  🌐  LIVE HTTP SNIFFER (port 80)                           │${NC}"
    echo -e "${CYAN}│     Shows URLs / domains devices are browsing               │${NC}"
    echo -e "${CYAN}│     Press CTRL+C to stop                                    │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}\n"

    if [ "$HAS_ROOT" -eq 1 ]; then
        tcpdump -i "$HOTSPOT_IFACE" -tnl -s0 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)' 2>/dev/null | \
        while IFS= read -r packet; do
            timestamp=$(date '+%H:%M:%S')
            src=$(echo "$packet" | grep -oP '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
            dst=$(echo "$packet" | grep -oP '> [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sed 's/> //')
            http_data=$(echo "$packet" | grep -oiE '(GET|POST|PUT|DELETE) [^\"]+ HTTP' | head -1)

            if [ -n "$http_data" ]; then
                echo -e "[${timestamp}] ${GREEN}${src}${NC} → ${YELLOW}${http_data}${NC}"
            fi
        done
    else
        echo -e "${YELLOW}[!] HTTP sniffing requires root (tsu).${NC}\n"
        sleep 2
    fi
}

# ─── Real-time device activity log (summary) ────────────────────────────────
dashboard() {
    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  📊  DASHBOARD — Auto-refresh every 10s                     │${NC}"
    echo -e "${CYAN}│     Shows recent DNS + connected devices                    │${NC}"
    echo -e "${CYAN}│     Press CTRL+C to stop                                    │${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────┘${NC}\n"

    local logfile="/tmp/hotspot_monitor_$$.log"

    # Background sniffer writing to log
    if [ "$HAS_ROOT" -eq 1 ]; then
        tcpdump -i "$HOTSPOT_IFACE" -tnl -s0 port 53 2>/dev/null | \
        while IFS= read -r line; do
            domain=$(echo "$line" | grep -oP '(A\?|AAAA\?)\s+\K[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
            src=$(echo "$line" | grep -oP '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')
            [ -n "$domain" ] && echo "$(date '+%H:%M:%S') | $src | $domain" >> "$logfile"
        done &
        SNIFFER_PID=$!
    fi

    loop=0
    while true; do
        clear
        banner
        echo -e "${CYAN}───────────  DASHBOARD  ───────────${NC}\n"

        # Scan devices
        local subnet
        subnet=$(echo "$HOTSPOT_NET" | cut -d'/' -f1 | awk -F. '{print $1"."$2"."$3".0/24"}')
        echo -e "${BOLD}${GREEN}📡 Connected Devices:${NC}"
        nmap -sn -n "$subnet" --exclude "$(echo "$HOTSPOT_NET" | cut -d'/' -f1)" 2>/dev/null | \
            grep -E 'Nmap scan report for|MAC Address' | paste - - | \
            while IFS= read -r dev; do
                ip=$(echo "$dev" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
                mac=$(echo "$dev" | grep -oP '[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}')
                vendor=$(vendor_from_mac "$mac")
                echo -e "  ${GREEN}►${NC} $ip  │  $vendor"
            done

        # Recent activity
        echo -e "\n${BOLD}${YELLOW}🔍 Recent DNS Queries (last 20):${NC}"
        if [ -f "$logfile" ]; then
            tail -20 "$logfile" | while IFS='|' read -r ts src dom; do
                echo -e "  ${CYAN}[${ts}]${NC} ${GREEN}${src}${NC} → ${dom}"
            done
        else
            echo -e "  ${YELLOW}(waiting for traffic...)${NC}"
        fi

        loop=$((loop + 1))
        echo -e "\n${BOLD}${CYAN}Refresh #${loop} — next in 10s... (CTRL+C to exit)${NC}"
        sleep 10
    done

    # Cleanup
    [ -n "$SNIFFER_PID" ] && kill "$SNIFFER_PID" 2>/dev/null
    rm -f "$logfile"
}

# ─── Main menu ───────────────────────────────────────────────────────────────
main() {
    banner
    check_deps
    find_iface

    echo -e "${GREEN}[✓] Hotspot interface: $HOTSPOT_IFACE${NC}"
    echo -e "${GREEN}[✓] Network:          $HOTSPOT_NET${NC}"
    echo -e "${GREEN}[✓] Root available:    $([ "$HAS_ROOT" -eq 1 ] && echo 'YES' || echo 'NO')${NC}"
    echo ""

    while true; do
        echo -e "${BOLD}${CYAN}Choose a monitoring mode:${NC}"
        echo -e "  ${GREEN}1${NC})  Scan connected devices (one-time)"
        echo -e "  ${GREEN}2${NC})  Live DNS sniffer (see what domains they visit)"
        echo -e "  ${GREEN}3${NC})  Live HTTP sniffer (see URLs they browse, root only)"
        echo -e "  ${GREEN}4${NC})  📊 Dashboard (auto-refresh, devices + DNS)"
        echo -e "  ${GREEN}q${NC})  Quit"
        echo ""
        read -rp "  $ Choice: " choice

        case "$choice" in
            1) scan_devices ;;
            2) dns_sniff ;;
            3) http_sniff ;;
            4) dashboard ;;
            q|Q) echo -e "\n${GREEN}[+] Exiting. Stay sharp.${NC}"; exit 0 ;;
            *) echo -e "${RED}[!] Invalid choice.${NC}" ;;
        esac

        echo -e "\n${YELLOW}Press ENTER to return to menu...${NC}"
        read -r
        banner
        echo -e "${GREEN}[✓] Hotspot interface: $HOTSPOT_IFACE${NC}"
        echo -e "${GREEN}[✓] Network:          $HOTSPOT_NET${NC}"
        echo ""
    done
}

# ─── Trap ────────────────────────────────────────────────────────────────────
trap 'echo -e "\n${RED}[!] Interrupted.${NC}"; exit 1' INT TERM

# ─── Go ──────────────────────────────────────────────────────────────────────
main "$@"
