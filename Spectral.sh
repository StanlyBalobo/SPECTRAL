#!/bin/bash

#==============================================================#
#                                                              #
#   ███████╗██████╗ ███████╗ ██████╗████████╗██████╗  █████╗  #
#   ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗ #
#   ███████╗██████╔╝█████╗  ██║        ██║   ██████╔╝███████║ #
#   ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══██╗██╔══██║ #
#   ███████║██║     ███████╗╚██████╗   ██║   ██║  ██║██║  ██║ #
#   ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ #
#                                                              #
#   🔍 Cyber Security Suite | v2.0                            #
#   🎯 "Your protection is your skill."                        #
#                                                              #
#==============================================================#

#------------------- COLOR DEFINITIONS ------------------------#
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DARK_GRAY='\033[1;30m'
LIGHT_GREEN='\033[1;92m'
LIGHT_RED='\033[1;91m'
LIGHT_BLUE='\033[1;94m'
LIGHT_MAGENTA='\033[1;95m'
LIGHT_CYAN='\033[1;96m'
NC='\033[0m'

#------------------- BANNER ----------------------------------#
show_banner() {
    clear
    echo -e "${LIGHT_RED}"
    echo "   ▄▄▄█████▓ ██░ ██  ▓█████  ██▀███   ▄▄▄       ██▓     ██▓███  "
    echo "   ▓  ██▒ ▓▒▓██░ ██▒ ▓█   ▀ ▓██ ▒ ██▒▒████▄    ▓██▒    ▓██░  ██▒"
    echo "   ▒ ▓██░ ▒░▒██▀▀██░ ▒███   ▓██ ░▄█ ▒▒██  ▀█▄  ▒██░    ▓██░ ██▓▒"
    echo "   ░ ▓██▓ ░ ░▓█ ░██  ▒▓█  ▄ ▒██▀▀█▄  ░██▄▄▄▄██ ▒██░    ▒██▄█▓▒ ▒"
    echo "     ▒██▒ ░ ░▓█▒░██▓ ░▒████▒░██▓ ▒██▒ ▓█   ▓██▒░██████▒▒██▒ ░  ░"
    echo "     ▒ ░░    ▒ ░░▒░▒ ░░ ▒░ ░░ ▒▓ ░▒▓░ ▒▒   ▓▒█░░ ▒░▓  ░▒▓▒░ ░  ░"
    echo "       ░     ▒ ░▒░ ░  ░ ░  ░  ░▒ ░ ▒░  ▒   ▒▒ ░░ ░ ▒  ░░▒ ░     "
    echo "     ░       ░  ░░ ░    ░     ░░   ░   ░   ▒     ░ ░   ░░       "
    echo "             ░  ░  ░    ░  ░   ░           ░  ░    ░  ░         "
    echo -e "${NC}"
    echo -e "${LIGHT_CYAN}   ╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${LIGHT_CYAN}   ║${NC}  ${WHITE}CYBER SECURITY SUITE${NC}  |  ${YELLOW}v2.0${NC}  |  ${BLUE}Spectral${NC}      ${LIGHT_CYAN}║${NC}"
    echo -e "${LIGHT_CYAN}   ║${NC}  ${LIGHT_GREEN}⚡ Free + Tor + Proxy Rotator${NC}              ${LIGHT_CYAN}║${NC}"
    echo -e "${LIGHT_CYAN}   ╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "   ${DARK_GRAY}┌──────────────────────────────────────────────────┐${NC}"
    echo -e "   ${DARK_GRAY}│${NC}  ${WHITE}OS:${NC}  ${LIGHT_GREEN}$(uname -o 2>/dev/null || echo "Android/Linux")${NC}"
    echo -e "   ${DARK_GRAY}│${NC}  ${WHITE}Date:${NC} ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    PROXY_COUNT=$(cat /tmp/spectral_proxies.txt 2>/dev/null | wc -l)
    [ "$PROXY_COUNT" -gt 0 ] && \
    echo -e "   ${DARK_GRAY}│${NC}  ${WHITE}Proxies:${NC} ${GREEN}$PROXY_COUNT loaded${NC}" || \
    echo -e "   ${DARK_GRAY}│${NC}  ${WHITE}Proxies:${NC} ${YELLOW}Not loaded yet${NC}"
    echo -e "   ${DARK_GRAY}└──────────────────────────────────────────────────┘${NC}"
    echo ""
}

#------------------- DEPENDENCIES ----------------------------#
check_deps() {
    local missing=0
    
    if command -v termux-setup-storage &>/dev/null; then
        for pkg in tor curl nmap python3 netcat-openbsd; do
            if ! command -v $pkg &>/dev/null; then
                echo -e "${YELLOW}[*] Installing $pkg...${NC}"
                pkg install -y "$pkg" 2>/dev/null || missing=1
            fi
        done
    else
        for cmd in tor curl nmap python3 nc; do
            if ! command -v $cmd &>/dev/null; then
                echo -e "${YELLOW}[*] Installing $cmd...${NC}"
                sudo apt install -y "$cmd" 2>/dev/null || \
                sudo pacman -S --noconfirm "$cmd" 2>/dev/null || missing=1
            fi
        done
    fi
    
    pip3 install colorama requests 2>/dev/null
}

#------------------- FREE PROXY LOADER -----------------------#
load_free_proxies() {
    echo -e "${YELLOW}[*] Fetching free proxy list (updated every 2 min)...${NC}"
    
    # Download from multiple free proxy sources
    # Source 1: komutan234 (SOCKS5)
    curl -sL "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/socks5.txt" -o /tmp/spectral_proxies_socks5.txt &
    
    # Source 2: komutan234 (HTTP)
    curl -sL "https://raw.githubusercontent.com/komutan234/Proxy-List-Free/main/proxies/http.txt" -o /tmp/spectral_proxies_http.txt &
    
    # Source 3: ProxyScrape
    curl -sL "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all" -o /tmp/spectral_proxies_scrape.txt &
    
    wait
    
    # Combine and deduplicate
    cat /tmp/spectral_proxies_socks5.txt /tmp/spectral_proxies_http.txt /tmp/spectral_proxies_scrape.txt 2>/dev/null | \
        grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' | \
        sort -u > /tmp/spectral_proxies.txt
    
    local count=$(wc -l < /tmp/spectral_proxies.txt 2>/dev/null || echo 0)
    
    if [ "$count" -gt 0 ]; then
        echo -e "${GREEN}[+] Loaded ${WHITE}$count${GREEN} free proxies!${NC}"
    else
        echo -e "${YELLOW}[!] No proxies fetched. Falling back to Tor only.${NC}"
    fi
}

#------------------- TEST PROXY ------------------------------#
test_proxy() {
    local proxy=$1
    local result=$(curl -s --max-time 3 --proxy "socks5://$proxy" https://api64.ipify.org 2>/dev/null)
    if [ -n "$result" ] && [ "$result" != "null" ]; then
        echo "$result"
        return 0
    fi
    return 1
}

#------------------- GET LOCATION FROM IP --------------------#
get_location() {
    local ip=$1
    local info=$(curl -s --max-time 3 "http://ip-api.com/json/$ip" 2>/dev/null)
    if [ -n "$info" ]; then
        echo "$info"
    fi
}

#==================================================================#
#                OPTION 1: IP FAST CHANGER (Enhanced)              #
#==================================================================#
ip_fast_changer() {
    clear
    echo -e "${RED}"
    echo "   ╔══════════════════════════════════════════════════╗"
    echo "   ║           🔄 IP FAST CHANGER v2.0               ║"
    echo "   ║    ${WHITE}Tor + Free Proxy Multi-Engine${RED}                ║"
    echo "   ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${YELLOW}[*] Choose rotation engine:${NC}"
    echo -e "  ${GREEN}[1]${NC} ${WHITE}Tor Engine${NC}     - ${DARK_GRAY}Free, stable, 5+ countries${NC}"
    echo -e "  ${GREEN}[2]${NC} ${WHITE}Proxy Engine${NC}    - ${DARK_GRAY}Free proxies, 50+ countries${NC}"
    echo -e "  ${GREEN}[3]${NC} ${WHITE}Hybrid Engine${NC}   - ${DARK_GRAY}Tor + Proxies (MAX rotation)${NC}"
    echo ""
    read -p "$(echo -e "${LIGHT_CYAN}[?] Choose engine [1]: ${NC}")" ENGINE
    ENGINE=${ENGINE:-1}
    
    echo ""
    echo -e "${YELLOW}[*] Rotation interval in seconds${NC}"
    echo -e "${DARK_GRAY}    (Recommended: 8-15 for Tor, 5-10 for Proxy)${NC}"
    read -p "$(echo -e "${LIGHT_CYAN}[?] Interval [10]: ${NC}")" INTERVAL
    INTERVAL=${INTERVAL:-10}
    
    echo ""
    echo -e "${GREEN}[*] Starting IP rotation every ${WHITE}$INTERVAL${GREEN} seconds...${NC}"
    echo -e "${RED}[!] Press CTRL+C to stop${NC}"
    sleep 2
    
    COUNT=1
    
    case $ENGINE in
        1)  # TOR ENGINE
            echo -e "${YELLOW}[*] Initializing Tor...${NC}"
            killall tor 2>/dev/null
            cat > /tmp/torrc_spectral << 'EOF'
SocksPort 9050
ControlPort 9051
HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072090276A3B3F2B8D8D9A8D9
CookieAuthentication 0
DataDirectory /tmp/tor_data_spec
NewCircuitPeriod 1
MaxCircuitDirtiness 1
EOF
            tor -f /tmp/torrc_spectral 2>/dev/null &
            sleep 5
            
            while true; do
                # Request new Tor circuit
                (echo authenticate '"SpectralRotator123"'; echo signal newnym; echo quit) | nc 127.0.0.1 9051 2>/dev/null
                sleep 3
                
                NEW_IP=$(curl -s --socks5 127.0.0.1:9050 --max-time 5 https://api64.ipify.org 2>/dev/null)
                
                if [ -n "$NEW_IP" ]; then
                    INFO=$(curl -s --max-time 3 "http://ip-api.com/json/$NEW_IP" 2>/dev/null)
                    COUNTRY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('country','?'))" 2>/dev/null)
                    CITY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('city','?'))" 2>/dev/null)
                    ISP=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('isp','?'))" 2>/dev/null)
                    
                    echo -e "${LIGHT_GREEN}[${COUNT}]${NC} ${WHITE}IP:${NC} ${LIGHT_GREEN}$NEW_IP${NC}"
                    echo -e "      ${LIGHT_BLUE}├── ${WHITE}Location:${NC} ${YELLOW}$CITY, $COUNTRY${NC}"
                    echo -e "      ${LIGHT_BLUE}└── ${WHITE}ISP:${NC} ${DARK_GRAY}$ISP${NC}"
                else
                    echo -e "  ${RED}[!] Tor circuit failed, retrying...${NC}"
                fi
                
                ((COUNT++))
                for ((i=INTERVAL; i>0; i--)); do
                    echo -ne "\r  ${DARK_GRAY}Next rotation in: ${WHITE}$i${DARK_GRAY}s  ${NC}"
                    sleep 1
                done
                echo -ne "\r                                        \r"
            done
            ;;
            
        2)  # PROXY ENGINE (Free proxies only)
            load_free_proxies
            local proxy_list=()
            mapfile -t proxy_list < /tmp/spectral_proxies.txt
            
            if [ ${#proxy_list[@]} -eq 0 ]; then
                echo -e "${RED}[!] No proxies available. Try Tor engine instead.${NC}"
                sleep 2
                return
            fi
            
            echo -e "${GREEN}[+] Loaded ${#proxy_list[@]} proxies. Testing live ones...${NC}"
            local live_proxies=()
            for proxy in "${proxy_list[@]:0:50}"; do
                echo -ne "\r  ${DARK_GRAY}Testing proxy: $proxy  ${NC}"
                IP=$(test_proxy "$proxy")
                if [ -n "$IP" ]; then
                    live_proxies+=("$proxy")
                    echo -e "\r  ${GREEN}[✓]${NC} $proxy → ${LIGHT_GREEN}$IP${NC}"
                fi
            done
            
            if [ ${#live_proxies[@]} -eq 0 ]; then
                echo -e "\n${RED}[!] No live proxies found. Try again later.${NC}"
                sleep 2
                return
            fi
            
            echo -e "\n${GREEN}[+] ${#live_proxies[@]} live proxies ready!${NC}"
            sleep 2
            
            while true; do
                local idx=$((RANDOM % ${#live_proxies[@]}))
                local proxy="${live_proxies[$idx]}"
                
                NEW_IP=$(curl -s --max-time 5 --proxy "socks5://$proxy" https://api64.ipify.org 2>/dev/null)
                
                if [ -n "$NEW_IP" ]; then
                    INFO=$(curl -s --max-time 3 "http://ip-api.com/json/$NEW_IP" 2>/dev/null)
                    COUNTRY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('country','?'))" 2>/dev/null)
                    CITY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('city','?'))" 2>/dev/null)
                    
                    echo -e "${LIGHT_GREEN}[${COUNT}]${NC} ${WHITE}IP:${NC} ${LIGHT_GREEN}$NEW_IP${NC}"
                    echo -e "      ${LIGHT_BLUE}├── ${WHITE}Proxy:${NC} ${DARK_GRAY}$proxy${NC}"
                    echo -e "      ${LIGHT_BLUE}├── ${WHITE}Location:${NC} ${YELLOW}$CITY, $COUNTRY${NC}"
                    echo -e "      ${LIGHT_BLUE}└── ${WHITE}Remaining:${NC} ${GREEN}${#live_proxies[@]} proxies${NC}"
                else
                    echo -e "  ${RED}[!] Dead proxy, removing...${NC}"
                    unset 'live_proxies[$idx]'
                    live_proxies=("${live_proxies[@]}")
                    if [ ${#live_proxies[@]} -eq 0 ]; then
                        echo -e "${RED}[!] All proxies dead. Reloading...${NC}"
                        load_free_proxies
                        break
                    fi
                fi
                
                ((COUNT++))
                for ((i=INTERVAL; i>0; i--)); do
                    echo -ne "\r  ${DARK_GRAY}Next rotation in: ${WHITE}$i${DARK_GRAY}s  ${NC}"
                    sleep 1
                done
                echo -ne "\r                                        \r"
            done
            ;;
            
        3)  # HYBRID ENGINE (Tor + Proxies)
            echo -e "${YELLOW}[*] Starting Hybrid Engine (Tor base + Proxy rotation)...${NC}"
            killall tor 2>/dev/null
            cat > /tmp/torrc_spectral << 'EOF'
SocksPort 9050
ControlPort 9051
HashedControlPassword 16:872860B76453A77D60CA2BB8C1A7042072090276A3B3F2B8D8D9A8D9
CookieAuthentication 0
DataDirectory /tmp/tor_data_spec
NewCircuitPeriod 1
MaxCircuitDirtiness 1
EOF
            tor -f /tmp/torrc_spectral 2>/dev/null &
            sleep 5
            
            load_free_proxies
            
            while true; do
                # Alternating: Tor then Proxy then Tor then Proxy...
                if ((COUNT % 2 == 1)); then
                    # Use Tor
                    (echo authenticate '"SpectralRotator123"'; echo signal newnym; echo quit) | nc 127.0.0.1 9051 2>/dev/null
                    sleep 3
                    NEW_IP=$(curl -s --socks5 127.0.0.1:9050 --max-time 5 https://api64.ipify.org 2>/dev/null)
                    ENGINE_USED="Tor"
                else
                    # Use a free proxy
                    local proxy_line=$(shuf -n 1 /tmp/spectral_proxies.txt 2>/dev/null)
                    if [ -n "$proxy_line" ]; then
                        NEW_IP=$(curl -s --max-time 5 --proxy "socks5://$proxy_line" https://api64.ipify.org 2>/dev/null)
                        ENGINE_USED="Proxy:$proxy_line"
                    else
                        NEW_IP=""
                        ENGINE_USED="Failed"
                    fi
                fi
                
                if [ -n "$NEW_IP" ]; then
                    INFO=$(curl -s --max-time 3 "http://ip-api.com/json/$NEW_IP" 2>/dev/null)
                    COUNTRY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('country','?'))" 2>/dev/null)
                    CITY=$(echo "$INFO" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('city','?'))" 2>/dev/null)
                    
                    echo -e "${LIGHT_GREEN}[${COUNT}]${NC} ${WHITE}Engine:${NC} ${MAGENTA}$ENGINE_USED${NC}"
                    echo -e "      ${LIGHT_BLUE}├── ${WHITE}IP:${NC} ${LIGHT_GREEN}$NEW_IP${NC}"
                    echo -e "      ${LIGHT_BLUE}└── ${WHITE}Location:${NC} ${YELLOW}$CITY, $COUNTRY${NC}"
                else
                    echo -e "  ${RED}[!] Rotation failed on $ENGINE_USED${NC}"
                fi
                
                ((COUNT++))
                for ((i=INTERVAL; i>0; i--)); do
                    echo -ne "\r  ${DARK_GRAY}Next rotation in: ${WHITE}$i${DARK_GRAY}s  ${NC}"
                    sleep 1
                done
                echo -ne "\r                                        \r"
            done
            ;;
    esac
}

#==================================================================#
#                OPTION 2: DDOS ATTACK DEFENDER                    #
#==================================================================#
ddos_defender() {
    clear
    echo -e "${RED}"
    echo "   ╔══════════════════════════════════════════════════╗"
    echo "   ║          🛡️  DDOS ATTACK DEFENDER               ║"
    echo "   ║     ${WHITE}Monitor, Detect & Block${RED}                        ║"
    echo "   ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${WHITE}Select mode:${NC}"
    echo -e "  ${GREEN}[1]${NC} ${WHITE}Live Connection Monitor${NC}"
    echo -e "  ${GREEN}[2]${NC} ${WHITE}Auto-Block Suspicious IPs${NC}"
    echo -e "  ${GREEN}[3]${NC} ${WHITE}Connection Stats & Analysis${NC}"
    echo -e "  ${GREEN}[0]${NC} ${WHITE}Back${NC}"
    echo ""
    read -p "$(echo -e "${LIGHT_CYAN}[?] Choose: ${NC}")" DDOS_CHOICE
    
    case $DDOS_CHOICE in
        1)
            clear
            echo -e "${YELLOW}[*] Live Connection Monitor (refreshes every 3s)${NC}"
            INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
            
            while true; do
                clear
                echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
                echo -e "${RED}║${NC}  ${WHITE}LIVE CONNECTION MONITOR — $INTERFACE${NC}           ${RED}║${NC}"
                echo -e "${RED}║${NC}  ${DARK_GRAY}$(date '+%Y-%m-%d %H:%M:%S')${NC}                               ${RED}║${NC}"
                echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
                echo ""
                echo -e "${CYAN}  PROTO  LOCAL           FOREIGN          STATE${NC}"
                echo -e "${DARK_GRAY}  ─────────────────────────────────────────────────────────${NC}"
                
                ss -tunpa 2>/dev/null | grep -v "State" | head -30 | while read line; do
                    proto=$(echo $line | awk '{print $1}')
                    local_addr=$(echo $line | awk '{print $4}')
                    foreign=$(echo $line | awk '{print $5}')
                    state=$(echo $line | awk '{print $2}')
                    
                    case $state in
                        ESTAB)  color=$GREEN ;;
                        SYN-RECV) color=$RED ;;
                        TIME-WAIT) color=$YELLOW ;;
                        *)      color=$DARK_GRAY ;;
                    esac
                    
                    printf "  ${color}%-5s %-18s %-21s %-10s${NC}\n" "$proto" "$local_addr" "$foreign" "$state"
                done
                
                echo ""
                TOTAL=$(ss -tun | wc -l)
                ESTAB=$(ss -tun state established | wc -l 2>/dev/null || echo 0)
                SYN_RECV=$(ss -tun state syn-recv | wc -l 2>/dev/null || echo 0)
                TIME_WAIT=$(ss -tun state time-wait | wc -l 2>/dev/null || echo 0)
                
                echo -e "  ${WHITE}Stats:${NC}  ${GREEN}Established: $ESTAB${NC}  ${RED}SYN-RECV: $SYN_RECV${NC}  ${YELLOW}Time-Wait: $TIME_WAIT${NC}  ${DARK_GRAY}Total: $TOTAL${NC}"
                
                if [ "$SYN_RECV" -gt 100 ]; then
                    echo -e "  ${LIGHT_RED}⚠ WARNING: Possible SYN Flood detected! ($SYN_RECV connections)${NC}"
                fi
                
                sleep 3
            done
            ;;
            
        2)
            clear
            echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║${NC}  ${WHITE}AUTO-BLOCK SUSPICIOUS IPs${NC}                        ${RED}║${NC}"
            echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "${YELLOW}[*] Monitoring for DDoS patterns...${NC}"
            
            while true; do
                clear
                echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
                echo -e "${RED}║${NC}  ${WHITE}CONNECTION ANALYSIS — $(date '+%H:%M:%S')${NC}           ${RED}║${NC}"
                echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
                echo ""
                
                # Get IPs sorted by connection count
                ss -tun | grep -vE "State|LISTEN" | awk '{print $5}' | awk -F: '{print $1}' | grep -E '^[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -15 | while read count ip; do
                    if [ "$count" -gt 100 ]; then
                        echo -e "  ${LIGHT_RED}🚫 ${WHITE}$ip${NC} — ${RED}$count connections [BLOCKED]${NC}"
                        iptables -A INPUT -s "$ip" -j DROP 2>/dev/null
                    elif [ "$count" -gt 50 ]; then
                        echo -e "  ${YELLOW}⚠ ${WHITE}$ip${NC} — ${YELLOW}$count connections [Suspicious]${NC}"
                    else
                        echo -e "  ${GREEN}✓ ${WHITE}$ip${NC} — ${GREEN}$count connections${NC}"
                    fi
                done
                
                echo ""
                echo -e "${DARK_GRAY}[*] Blocked IPs: $(iptables -L INPUT -n 2>/dev/null | grep DROP | wc -l)${NC}"
                echo -e "${DARK_GRAY}[*] Checking again in 5s...${NC}"
                sleep 5
            done
            ;;
            
        3)
            clear
            echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║${NC}  ${WHITE}CONNECTION STATISTICS${NC}                        ${RED}║${NC}"
            echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
            echo ""
            
            TOTAL_CONN=$(ss -tun | wc -l)
            LISTEN=$(ss -tunl | wc -l)
            ESTAB=$(ss -tun state established | wc -l 2>/dev/null || echo 0)
            SYN_R=$(ss -tun state syn-recv | wc -l 2>/dev/null || echo 0)
            TW=$(ss -tun state time-wait | wc -l 2>/dev/null || echo 0)
            CLOSE_W=$(ss -tun state close-wait | wc -l 2>/dev/null || echo 0)
            
            echo -e "  ${WHITE}TCP/UDP Connection Summary:${NC}"
            echo -e "  ${GREEN}✓ Total Connections:${NC}  $TOTAL_CONN"
            echo -e "  ${GREEN}✓ Listening:${NC}          $LISTEN"
            echo -e "  ${GREEN}✓ Established:${NC}        $ESTAB"
            echo -e "  ${YELLOW}⏳ Time-Wait:${NC}         $TW"
            echo -e "  ${RED}⚠ SYN-RECV:${NC}          $SYN_R"
            echo -e "  ${RED}⚠ Close-Wait:${NC}        $CLOSE_W"
            
            echo ""
            echo -e "  ${WHITE}Top 5 Most Connected IPs:${NC}"
            ss -tun | grep -vE "State|LISTEN" | awk '{print $5}' | awk -F: '{print $1}' | grep -E '^[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -5 | while read count ip; do
                echo -e "  ${DARK_GRAY}  $count connections →${NC} ${WHITE}$ip${NC}"
            done
            
            echo ""
            read -p "$(echo -e "${DARK_GRAY}[Press Enter to continue]${NC}")"
            ;;
    esac
}

#==================================================================#
#                OPTION 3: WI-FI DEVICE SCANNER                    #
#==================================================================#
network_scanner() {
    clear
    echo -e "${MAGENTA}"
    echo "   ╔══════════════════════════════════════════════════╗"
    echo "   ║       📡 WI-FI DEVICE SCANNER                   ║"
    echo "   ║    ${WHITE}Detect all devices on your network${MAGENTA}            ║"
    echo "   ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Auto-detect network
    GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
    INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
    
    if command -v ifconfig &>/dev/null; then
        IP_ADDR=$(ifconfig "$INTERFACE" 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1 | grep -Eo '([0-9]*\.){3}[0-9]*')
    else
        IP_ADDR=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
    fi
    
    if [ -z "$IP_ADDR" ]; then
        echo -e "${YELLOW}[!] Could not detect your IP. Enter manually:${NC}"
        read -p "$(echo -e "${LIGHT_CYAN}[?] Your IP (e.g., 192.168.1.100): ${NC}")" IP_ADDR
    fi
    
    SUBNET=$(echo "$IP_ADDR" | cut -d. -f1-3)
    RANGE="${SUBNET}.0/24"
    
    echo -e "  ${WHITE}Your IP:${NC} ${GREEN}$IP_ADDR${NC}"
    echo -e "  ${WHITE}Gateway:${NC} ${GREEN}$GATEWAY${NC}"
    echo -e "  ${WHITE}Interface:${NC} ${GREEN}$INTERFACE${NC}"
    echo -e "  ${WHITE}Scanning:${NC} ${YELLOW}$RANGE${NC}"
    echo ""
    
    if command -v nmap &>/dev/null; then
        echo -e "${YELLOW}[*] Running fast ping scan...${NC}"
        echo ""
        echo -e "${CYAN}  ╔════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}  ║${NC}  ${WHITE}DEVICES ON YOUR NETWORK${NC}                 ${CYAN}║${NC}"
        echo -e "${CYAN}  ╚════════════════════════════════════════════╝${NC}"
        echo ""
        
        # Run scan
        nmap -sn "$RANGE" 2>/dev/null | while read line; do
            if echo "$line" | grep -q "Nmap scan report"; then
                DEV_IP=$(echo "$line" | grep -oP '(\d+\.){3}\d+')
                echo -ne "\n  ${GREEN}📡 ${WHITE}$DEV_IP${NC}"
            elif echo "$line" | grep -q "Host is up"; then
                LATENCY=$(echo "$line" | grep -oP '[0-9]+\.[0-9]+s' || echo "?")
                echo -ne " ${GREEN}[UP - ${LATENCY}]${NC}"
            elif echo "$line" | grep -q "MAC Address"; then
                MAC=$(echo "$line" | grep -oP '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}')
                VENDOR=$(echo "$line" | grep -oP '(?<=\().*(?=\))')
                echo -e "\n  ${DARK_GRAY}    └── MAC: ${WHITE}$MAC${NC} ${YELLOW}($VENDOR)${NC}"
            fi
        done
        
        echo ""
        echo ""
        echo -e "${YELLOW}[*] Running service scan on active hosts...${NC}"
        echo ""
        nmap -sV -F "$RANGE" 2>/dev/null | grep -E "Nmap scan report for|PORT|open|OS details" | head -40
        
    else
        # Fallback ping sweep
        echo -e "${YELLOW}[!] nmap not found. Using ping sweep...${NC}"
        echo ""
        for i in $(seq 1 254); do
            IP="${SUBNET}.$i"
            (
                if ping -c 1 -W 1 "$IP" 2>/dev/null | grep -q "1 received"; then
                    echo -e "  ${GREEN}[+] ${WHITE}$IP${NC} ${GREEN}is UP${NC}"
                fi
            ) &
        done
        wait
    fi
    
    echo ""
    echo -e "${DARK_GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}💡 Tip: For deeper scanning use:${NC}"
    echo -e "${CYAN}   nmap -sV -A -O ${RANGE}${NC}"
    echo ""
    read -p "$(echo -e "${DARK_GRAY}[Press Enter for menu]${NC}")"
}

#==================================================================#
#                       MAIN MENU                                 #
#==================================================================#
trap 'echo -e "\n${YELLOW}[!] Returning...${NC}"; sleep 1' INT
trap 'killall tor 2>/dev/null; echo -e "\n${LIGHT_RED}Spectral terminated.${NC}"' EXIT

check_deps

while true; do
    show_banner
    
    echo -e "  ${LIGHT_CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}  ${WHITE}          SPECTRAL MAIN MENU${NC}          ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}                                      ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}  ${GREEN}[1]${NC}  ${WHITE}🔄 IP Fast Changer${NC}              ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}     ${DARK_GRAY} Tor | Free Proxy | Hybrid${NC}         ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}                                      ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}  ${RED}[2]${NC}  ${WHITE}🛡️  DDoS Attack Defender${NC}          ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}     ${DARK_GRAY} Monitor | Block | Analyze${NC}          ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}                                      ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}  ${MAGENTA}[3]${NC}  ${WHITE}📡 Wi-Fi Device Scanner${NC}          ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}     ${DARK_GRAY} Scan all network devices${NC}            ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}                                      ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}  ${RED}[0]${NC}  ${WHITE}🚪 Exit${NC}                         ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}║${NC}                                      ${LIGHT_CYAN}║${NC}"
    echo -e "  ${LIGHT_CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -ne "  ${LIGHT_GREEN}━━━▶ ${WHITE}Spectral${DARK_GRAY}@${WHITE}root${NC} ${DARK_GRAY}➜${NC} "
    read CHOICE
    
    case $CHOICE in
        1) ip_fast_changer ;;
        2) ddos_defender ;;
        3) network_scanner ;;
        0)
            echo ""
            echo -e "${LIGHT_CYAN}   ╔════════════════════════════════════════╗${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}  ${YELLOW}\"The only way to do great work${NC}      ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}  ${YELLOW} is to love what you do.\"${NC}            ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}  ${DARK_GRAY}— Steve Jobs${NC}                      ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}                                      ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}  ${GREEN}Keep building. Your FBI journey${NC}     ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ║${NC}  ${GREEN}starts with what you learn today.${NC}  ${LIGHT_CYAN}║${NC}"
            echo -e "${LIGHT_CYAN}   ╚════════════════════════════════════════╝${NC}"
            echo ""
            exit 0
            ;;
        *) echo -e "${RED}  [!] Invalid option${NC}"; sleep 1 ;;
    esac
done