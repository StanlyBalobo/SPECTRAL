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
#  [+] Target: +63 (Philippines) numbers
#  [+] Features: Bulk send, delay control, count control
#  [+] Usage:  chmod +x sms_blaster.sh && ./sms_blaster.sh
#

# ============================================================
# CONFIGURATION
# ============================================================
# --- Choose your SMS gateway ---
# "textbelt"  = Textbelt (free: 1 SMS/day, paid: unlimited) 
# "twilio"    = Twilio (requires ACCOUNT SID & AUTH TOKEN)
# "custom"    = Custom HTTP endpoint
GATEWAY="textbelt"

# --- Twilio credentials (only needed if GATEWAY="twilio") ---
TWILIO_SID=""
TWILIO_TOKEN=""
TWILIO_FROM=""          # Your Twilio phone number (e.g., +18551234567)

# --- Custom gateway (only needed if GATEWAY="custom") ---
CUSTOM_URL=""
CUSTOM_METHOD="POST"    # POST or GET
CUSTOM_PHONE_PARAM="phone"
CUSTOM_MSG_PARAM="message"
CUSTOM_HEADER=""        # e.g. "Authorization: Bearer YOUR_TOKEN"

# ============================================================
# FUNCTIONS
# ============================================================

banner() {
    echo -e "\e[1;31m"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║        SMS BLASTER - Bulk SMS Sender Tool           ║"
    echo "║      For Authorized Penetration Testing Only        ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "\e[0m"
}

validate_phone() {
    local phone="$1"
    # Strip any non-digit characters
    phone=$(echo "$phone" | tr -cd '0-9')
    
    # Check if it's a valid +63 number
    if [[ "${#phone}" -eq 10 ]] && [[ "$phone" =~ ^9[0-9]{9}$ ]]; then
        echo "63${phone:1}"
    elif [[ "${#phone}" -eq 11 ]] && [[ "$phone" =~ ^09[0-9]{9}$ ]]; then
        echo "63${phone:2}"
    elif [[ "${#phone}" -eq 12 ]] && [[ "$phone" =~ ^639[0-9]{9}$ ]]; then
        echo "$phone"
    elif [[ "${#phone}" -eq 13 ]] && [[ "$phone" =~ ^\+639[0-9]{9}$ ]]; then
        echo "${phone:1}"
    else
        echo "INVALID"
    fi
}

send_sms_textbelt() {
    local phone="$1"
    local message="$2"
    
    response=$(curl -s -X POST https://textbelt.com/text \
        --data-urlencode "phone=$phone" \
        --data-urlencode "message=$message" \
        -d key=textbelt)
    
    echo "$response"
}

send_sms_twilio() {
    local phone="$1"
    local message="$2"
    
    response=$(curl -s -X POST "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_SID/Messages" \
        --data-urlencode "Body=$message" \
        --data-urlencode "From=$TWILIO_FROM" \
        --data-urlencode "To=$phone" \
        -u "$TWILIO_SID:$TWILIO_TOKEN")
    
    echo "$response"
}

send_sms_custom() {
    local phone="$1"
    local message="$2"
    
    if [[ "$CUSTOM_METHOD" == "GET" ]]; then
        response=$(curl -s -G "$CUSTOM_URL" \
            --data-urlencode "$CUSTOM_PHONE_PARAM=$phone" \
            --data-urlencode "$CUSTOM_MSG_PARAM=$message" \
            -H "$CUSTOM_HEADER")
    else
        response=$(curl -s -X POST "$CUSTOM_URL" \
            --data-urlencode "$CUSTOM_PHONE_PARAM=$phone" \
            --data-urlencode "$CUSTOM_MSG_PARAM=$message" \
            -H "$CUSTOM_HEADER")
    fi
    
    echo "$response"
}

send_sms() {
    local phone="$1"
    local message="$2"
    local count="$3"
    local total="$4"
    
    case "$GATEWAY" in
        textbelt)
            result=$(send_sms_textbelt "$phone" "$message")
            ;;
        twilio)
            result=$(send_sms_twilio "$phone" "$message")
            ;;
        custom)
            result=$(send_sms_custom "$phone" "$message")
            ;;
        *)
            echo "ERROR: Unknown gateway '$GATEWAY'"
            return 1
            ;;
    esac
    
    # Parse result
    local success=$(echo "$result" | grep -o '"success":[^,}]*' | grep -o '[a-z]*$')
    local sms_id=$(echo "$result" | grep -o '"id":[^,}]*' | grep -o '[0-9]*')
    
    if [[ "$success" == "true" ]]; then
        echo -e "\e[1;32m[✓]\e[0m SMS $count/$total sent | ID: $sms_id"
        return 0
    else
        local error=$(echo "$result" | grep -o '"error":[^,}]*' | sed 's/"error"://' | sed 's/"//g')
        echo -e "\e[1;31m[✗]\e[0m SMS $count/$total FAILED | Reason: ${error:-Unknown}"
        return 1
    fi
}

# ============================================================
# MAIN
# ============================================================

banner

# --- Check prerequisites ---
if ! command -v curl &> /dev/null; then
    echo -e "\e[1;31m[!] ERROR: curl is not installed.\e[0m"
    echo "    Install it: sudo apt install curl -y"
    exit 1
fi

# --- Get phone number ---
echo -e "\e[1;36m[>]\e[0m Target phone number (+63 Philippines)"
read -p "  Phone: " RAW_PHONE

PHONE=$(validate_phone "$RAW_PHONE")
if [[ "$PHONE" == "INVALID" ]]; then
    echo -e "\e[1;31m[!] ERROR: Invalid phone number format.\e[0m"
    echo "    Accepted formats: 09171234567 | +639171234567 | 639171234567"
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
echo "    (use decimals for sub-second, e.g. 0.5)"
read -p "  Delay: " DELAY
if ! [[ "$DELAY" =~ ^[0-9]+\.?[0-9]*$ ]] || (( $(echo "$DELAY <= 0" | bc -l) )); then
    echo -e "\e[1;31m[!] ERROR: Enter a valid positive number.\e[0m"
    exit 1
fi
echo ""

# --- Summary ---
echo "╔══════════════════════════════════════════════════════╗"
echo "║                    JOB SUMMARY                       ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Gateway   : $(printf '%-36s' "$GATEWAY")║"
echo "║  Target    : +$(printf '%-36s' "$PHONE")║"
echo "║  Message   : $(printf '%-36s' "${MESSAGE:0:50}")║"
echo "║  Count     : $(printf '%-36s' "$COUNT")║"
echo "║  Delay     : $(printf '%-36s' "${DELAY}s")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

read -p "Proceed? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" ]] && [[ "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi
echo ""

# --- Send loop ---
echo -e "\e[1;35m[*] Firing SMS...\e[0m"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

for ((i = 1; i <= COUNT; i++)); do
    send_sms "$PHONE" "$MESSAGE" "$i" "$COUNT"
    if [[ $? -eq 0 ]]; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
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
echo "║  Sent     : $(printf '%-36s' "$SUCCESS_COUNT/$COUNT")║"
echo "║  Failed   : $(printf '%-36s' "$FAIL_COUNT")║"
echo "║  Duration : $(printf '%-36s' "${TOTAL_TIME}s")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
