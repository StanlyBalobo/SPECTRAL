#!/bin/bash
#
# ███████╗███╗   ███╗███████╗    ███████╗███████╗███╗   ██╗██████╗ 
# ██╔════╝████╗ ████║██╔════╝    ██╔════╝██╔════╝████╗  ██║██╔══██╗
# ███████╗██╔████╔██║███████╗    ███████╗█████╗  ██╔██╗ ██║██║  ██║
# ╚════██║██║╚██╔╝██║╚════██║    ╚════██║██╔══╝  ██║╚██╗██║██║  ██║
# ███████║██║ ╚═╝ ██║███████║    ███████║███████╗██║ ╚████║██████╔╝
# ╚══════╝╚═╝     ╚═╝╚══════╝    ╚══════╝╚══════╝╚═╝  ╚═══╝╚═════╝ 
#                                                                    
#  SMS Blaster - Authorized Penetration Testing Tool
#  [+] No API keys  |  No paid services  |  Fully offline
#  [+] Requires: USB GSM modem + active SIM card
#  [+] Backends: GAMMU (preferred) | MMCLI (fallback)
#

# ============================================================
# CONFIGURATION
# ============================================================
# Leave these blank for auto-detect, or force one:
#   "gammu"  -> uses gammu + USB modem
#   "mmcli"  -> uses ModemManager (mmcli)
#   "auto"   -> auto-detect which is available
BACKEND="auto"

# If your modem needs a PIN, set it here (leave blank if no PIN)
SIM_PIN=""

# ============================================================
# FUNCTIONS
# ============================================================

banner() {
    echo -e "\e[1;31m"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║        SMS BLASTER - Offline GSM Modem Tool         ║"
    echo "║      For Authorized Penetration Testing Only        ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "\e[0m"
}

validate_phone() {
    local phone="$1"
    phone=$(echo "$phone" | tr -cd '0-9')

    local len=${#phone}

    # 0917XXXXXXX (11 digits) -> 63917XXXXXXX
    if [[ "$len" -eq 11 ]] && [[ "$phone" =~ ^09[0-9]{9}$ ]]; then
        echo "63${phone:1}"
        return
    fi

    # +63917XXXXXXX stripped -> 63917XXXXXXX (12 digits)
    if [[ "$len" -eq 12 ]] && [[ "$phone" =~ ^639[0-9]{9}$ ]]; then
        echo "$phone"
        return
    fi

    # 917XXXXXXX (10 digits) -> 63917XXXXXXX
    if [[ "$len" -eq 10 ]] && [[ "$phone" =~ ^9[0-9]{9}$ ]]; then
        echo "63${phone}"
        return
    fi

    echo "INVALID"
}

# --- Detect backend ---
detect_backend() {
    if [[ "$BACKEND" != "auto" ]]; then
        echo "$BACKEND"
        return
    fi

    if command -v gammu &> /dev/null; then
        echo "gammu"
    elif command -v mmcli &> /dev/null; then
        echo "mmcli"
    else
        echo "NONE"
    fi
}

# --- Check gammu modem ---
check_gammu() {
    local output
    output=$(gammu identify 2>&1)
    if echo "$output" | grep -qi "Unknown" || echo "$output" | grep -qi "error\|Error\|FAIL\|not found"; then
        echo "FAILED"
    else
        echo "$output"
    fi
}

# --- Check mmcli modem ---
check_mmcli() {
    local modems
    modems=$(mmcli -L 2>&1)
    if echo "$modems" | grep -qi "No modems\|not found\|error"; then
        echo "FAILED"
    else
        # Extract first modem ID
        local modem_id
        modem_id=$(echo "$modems" | grep -oP '/org/freedesktop/ModemManager1/Modem/\K[0-9]+' | head -1)
        echo "$modem_id"
    fi
}

# --- Send via gammu ---
send_gammu() {
    local phone="$1"
    local message="$2"

    # gammu sendsms needs the number with + prefix for international
    echo "$message" | sudo gammu sendsms TEXT "+$phone" -unicode -report 2>&1
}

# --- Send via mmcli ---
send_mmcli() {
    local phone="$1"
    local message="$2"
    local modem_id="$3"

    # Create the SMS
    local create_out
    create_out=$(sudo mmcli -m "$modem_id" --messaging-create-sms="text='$message',number='+$phone'" 2>&1)
    
    # Extract SMS path
    local sms_path
    sms_path=$(echo "$create_out" | grep -oP '/org/freedesktop/ModemManager1/SMS/[0-9]+')
    
    if [[ -z "$sms_path" ]]; then
        echo "FAILED to create SMS: $create_out"
        return 1
    fi

    # Send the SMS
    local send_out
    send_out=$(sudo mmcli -s "$sms_path" --send 2>&1)
    
    # Delete the SMS from modem storage
    sudo mmcli -m "$modem_id" --messaging-delete-sms="$sms_path" &> /dev/null

    if echo "$send_out" | grep -qi "successfully sent"; then
        echo "SUCCESS"
    else
        echo "FAILED: $send_out"
    fi
}

# --- Send wrapper ---
send_sms() {
    local phone="$1"
    local message="$2"
    local count="$3"
    local total="$4"
    local backend="$5"
    local modem_id="$6"

    local result
    local status="?"

    if [[ "$backend" == "gammu" ]]; then
        result=$(send_gammu "$phone" "$message")
        if echo "$result" | grep -qi "OK\|reference="; then
            status="✓"
            return 0
        else
            status="✗"
            echo "$result"
            return 1
        fi
    elif [[ "$backend" == "mmcli" ]]; then
        result=$(send_mmcli "$phone" "$message" "$modem_id")
        if [[ "$result" == "SUCCESS" ]]; then
            status="✓"
            return 0
        else
            status="✗"
            echo "$result"
            return 1
        fi
    fi

    echo -e "\e[1;${color}m[${status}]\e[0m SMS $count/$total"
    echo "$result"
}

# ============================================================
# MAIN
# ============================================================

banner

# --- Prerequisites ---
if ! command -v curl &> /dev/null; then
    echo -e "\e[1;33m[!] Note: curl not installed (only needed for API gateways, not for GSM modem mode)\e[0m"
fi

if ! command -v sudo &> /dev/null; then
    echo -e "\e[1;31m[!] ERROR: sudo is required.\e[0m"
    exit 1
fi

# --- Detect backend ---
BACKEND=$(detect_backend)
if [[ "$BACKEND" == "NONE" ]]; then
    echo -e "\e[1;31m[!] ERROR: No GSM modem tool found.\e[0m"
    echo ""
    echo "    Install one of the following:"
    echo ""
    echo "    Option A: Gammu (recommended)"
    echo "      sudo apt update && sudo apt install gammu -y"
    echo "      Then configure: sudo gammu-config"
    echo "      (Set port: /dev/ttyUSB0, Connection: at19200)"
    echo ""
    echo "    Option B: ModemManager + mmcli"
    echo "      sudo apt install modemmanager mmcli -y"
    echo ""
    echo "    Then plug in your USB GSM modem and run this script again."
    exit 1
fi

echo -e "\e[1;33m[+] Backend detected: $BACKEND\e[0m"

# --- Verify modem ---
MODEM_ID=""
if [[ "$BACKEND" == "gammu" ]]; then
    echo -e "\e[1;36m[*] Checking gammu modem...\e[0m"
    gammu_check=$(check_gammu)
    if [[ "$gammu_check" == "FAILED" ]]; then
        echo -e "\e[1;31m[!] ERROR: gammu identify failed."
        echo "    Run 'sudo gammu-config' to set up your modem."
        echo "    Then run 'gammu identify' to test.\e[0m"
        exit 1
    fi
    echo -e "\e[1;32m[✓] Modem detected:\e[0m"
    echo "$gammu_check" | head -5
elif [[ "$BACKEND" == "mmcli" ]]; then
    echo -e "\e[1;36m[*] Checking mmcli modems...\e[0m"
    MODEM_ID=$(check_mmcli)
    if [[ "$MODEM_ID" == "FAILED" ]]; then
        echo -e "\e[1;31m[!] ERROR: No modem found via mmcli.\e[0m"
        echo "    Plug in your GSM modem and check: mmcli -L"
        echo "    If modem is listed but disabled: sudo mmcli -m 0 -e"
        exit 1
    fi
    echo -e "\e[1;32m[✓] Modem found: ID $MODEM_ID\e[0m"
    
    # Enable modem if needed
    modem_status=$(sudo mmcli -m "$MODEM_ID" --command "AT+CPIN?")
    if echo "$modem_status" | grep -qi "error\|SIM PIN"; then
        if [[ -n "$SIM_PIN" ]]; then
            echo -e "\e[1;33m[!] Unlocking SIM with PIN...\e[0m"
            sudo mmcli -m "$MODEM_ID" --pin "$SIM_PIN"
        else
            echo -e "\e[1;33m[!] SIM may be PIN-locked. Set SIM_PIN in the script.\e[0m"
        fi
    fi
fi

echo ""

# --- Get phone number ---
echo -e "\e[1;36m[>]\e[0m Target +63 phone number"
read -p "  Phone: " RAW_PHONE

PHONE=$(validate_phone "$RAW_PHONE")
if [[ "$PHONE" == "INVALID" ]]; then
    echo -e "\e[1;31m[!] ERROR: Invalid phone number."
    echo "    Formats: 0917XXXXXXX | +63917XXXXXXX | 63917XXXXXXX | 917XXXXXXX\e[0m"
    exit 1
fi
echo -e "  Normalized: \e[1;33m+$PHONE\e[0m"
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
echo -e "\e[1;36m[>]\e[0m How many times to send the message?"
read -p "  Count: " COUNT
if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [[ "$COUNT" -lt 1 ]]; then
    echo -e "\e[1;31m[!] ERROR: Enter a valid positive number.\e[0m"
    exit 1
fi
echo ""

# --- Get delay ---
echo -e "\e[1;36m[>]\e[0m Delay between each SMS (in seconds)"
echo "    (use decimals like 0.5 for sub-second)"
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
echo "║  Backend   : $(printf '%-36s' "$BACKEND")║"
echo "║  Target    : +$(printf '%-36s' "$PHONE")║"
echo "║  Message   : $(printf '%-36s' "${MESSAGE:0:50}")║"
echo "║  SMS Count : $(printf '%-36s' "$COUNT")║"
echo "║  Delay     : $(printf '%-36s' "${DELAY}s")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "Proceed? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" ]] && [[ "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi
echo ""

# --- Sending loop ---
echo -e "\e[1;35m[*] Sending SMS via modem...\e[0m"
echo ""

SUCCESS=0
FAIL=0
START_TIME=$(date +%s)

for ((i = 1; i <= COUNT; i++)); do
    echo -ne "\e[1;34m[→]\e[0m Sending $i/$COUNT... "
    
    if send_sms "$PHONE" "$MESSAGE" "$i" "$COUNT" "$BACKEND" "$MODEM_ID" 2>/dev/null; then
        echo -e "\e[1;32m✓\e[0m"
        ((SUCCESS++))
    else
        echo -e "\e[1;31m✗\e[0m"
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
