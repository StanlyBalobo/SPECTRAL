#!/bin/bash
#
#  SMS Blaster - Termux Native
#  [+] No API keys  |  No extra hardware
#  [+] Uses your phone's built-in SMS via Termux API
#

banner() {
    echo -e "\e[1;31m"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║        SMS BLASTER - Termux Edition                 ║"
    echo "║      For Authorized Penetration Testing Only        ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "\e[0m"
}

validate_phone() {
    local phone="$1"
    phone=$(echo "$phone" | tr -cd '0-9')
    local len=${#phone}

    # 0917XXXXXXX (11 digits) -> 917XXXXXXX (drop leading 0)
    if [[ "$len" -eq 11 ]] && [[ "$phone" =~ ^09[0-9]{9}$ ]]; then
        echo "${phone:1}"
        return
    fi

    # +63917XXXXXXX (stripped) -> 63917XXXXXXX (12 digits) -> 917XXXXXXX
    if [[ "$len" -eq 12 ]] && [[ "$phone" =~ ^639[0-9]{9}$ ]]; then
        echo "${phone:2}"
        return
    fi

    # 917XXXXXXX (10 digits) -> pass through
    if [[ "$len" -eq 10 ]] && [[ "$phone" =~ ^9[0-9]{9}$ ]]; then
        echo "$phone"
        return
    fi

    # 63917XXXXXXX (12 digits) -> 917XXXXXXX
    if [[ "$len" -eq 12 ]] && [[ "$phone" =~ ^639[0-9]{9}$ ]]; then
        echo "${phone:2}"
        return
    fi

    echo "INVALID"
}

banner

# --- Check termux-api ---
if ! command -v termux-sms-send &> /dev/null; then
    echo -e "\e[1;33m[!] termux-sms-send not found.\e[0m"
    echo "    Install: pkg install termux-api -y"
    echo ""
    read -p "    Install now? (y/N): " INSTALL
    if [[ "$INSTALL" == "y" || "$INSTALL" == "Y" ]]; then
        pkg install termux-api -y || { echo "Failed to install."; exit 1; }
    else
        exit 1
    fi
fi

# --- Request SMS permission (needed on first run) ---
echo -e "\e[1;36m[*] Checking SMS permissions...\e[0m"
termux-permission-send &> /dev/null
sleep 1
echo -e "\e[1;32m[✓] Permission requested (accept on phone if prompted)\e[0m"
echo ""

# --- Get phone number ---
echo -e "\e[1;36m[>]\e[0m Target +63 phone number"
read -p "  Phone: " RAW_PHONE

PHONE=$(validate_phone "$RAW_PHONE")
if [[ "$PHONE" == "INVALID" ]]; then
    echo -e "\e[1;31m[!] ERROR: Invalid phone number.\e[0m"
    echo "    Accepted: 0917XXXXXXX | +63917XXXXXXX | 63917XXXXXXX | 917XXXXXXX"
    exit 1
fi
echo -e "  Normalized: \e[1;33m0$PHONE\e[0m"
echo ""

# --- Get message ---
echo -e "\e[1;36m[>]\e[0m Message to send"
read -p "  Text: " MESSAGE
if [[ -z "$MESSAGE" ]]; then
    echo -e "\e[1;31m[!] ERROR: Message cannot be empty.\e[0m"
    exit 1
fi
echo ""

# --- Get count ---
echo -e "\e[1;36m[>]\e[0m How many times to send?"
read -p "  Count: " COUNT
if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [[ "$COUNT" -lt 1 ]]; then
    echo -e "\e[1;31m[!] ERROR: Enter a positive number.\e[0m"
    exit 1
fi
echo ""

# --- Get delay ---
echo -e "\e[1;36m[>]\e[0m Delay between each SMS (seconds)"
echo "    (use decimals for sub-second, e.g. 0.5)"
read -p "  Delay: " DELAY
if ! [[ "$DELAY" =~ ^[0-9]+\.?[0-9]*$ ]]; then
    echo -e "\e[1;31m[!] ERROR: Enter a valid number.\e[0m"
    exit 1
fi
echo ""

# --- Summary ---
echo "╔══════════════════════════════════════════════════════╗"
echo "║                    JOB SUMMARY                       ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Method    : Termux (Phone SMS)                      ║"
echo "║  Target    : 0$(printf '%-35s' "$PHONE")║"
echo "║  Message   : $(printf '%-36s' "${MESSAGE:0:50}")║"
echo "║  Count     : $(printf '%-36s' "$COUNT")║"
echo "║  Delay     : $(printf '%-36s' "${DELAY}s")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "Proceed? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi
echo ""

# --- Sending loop ---
echo -e "\e[1;35m[*] Sending SMS via phone...\e[0m"
echo ""

SUCCESS=0
FAIL=0
START_TIME=$(date +%s)

for ((i = 1; i <= COUNT; i++)); do
    echo -ne "\e[1;34m[→]\e[0m SMS $i/$COUNT... "
    
    # Send via Termux native API
    OUTPUT=$(termux-sms-send -n "0$PHONE" "$MESSAGE" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        echo -e "\e[1;32m✓\e[0m"
        ((SUCCESS++))
    else
        echo -e "\e[1;31m✗\e[0m"
        echo "    $OUTPUT"
        ((FAIL++))
    fi

    if [[ $i -lt $COUNT ]]; then
        sleep "$DELAY"
    fi
done

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                    RESULTS                           ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Sent     : $(printf '%-36s' "$SUCCESS/$COUNT")║"
echo "║  Failed   : $(printf '%-36s' "$FAIL")║"
echo "║  Duration : $(printf '%-36s' "${TOTAL_TIME}s")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
