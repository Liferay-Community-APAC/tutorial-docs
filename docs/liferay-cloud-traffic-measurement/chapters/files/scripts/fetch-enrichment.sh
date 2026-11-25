#!/usr/bin/env bash
# Download the IP enrichment data used by classify_traffic.py --data.
# Run weekly. Usage: fetch-enrichment.sh [data-dir]   (default: data)
set -euo pipefail
DATA="${1:-data}"
mkdir -p "$DATA"
curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o "$DATA/aws.json"
curl -fsSL https://www.gstatic.com/ipranges/cloud.json -o "$DATA/gcp.json"
curl -fsSL https://docs.oracle.com/iaas/tools/public_ip_ranges.json -o "$DATA/oracle.json"
curl -fsSL https://check.torproject.org/torbulkexitlist -o "$DATA/tor-exits.txt"

# Azure publishes its ranges as a weekly file whose URL changes each week.
# Copy the current "Azure IP Ranges and Service Tags - Public Cloud" download
# link from Microsoft's download page into AZURE_SERVICE_TAGS_URL to include it.
if [ -n "${AZURE_SERVICE_TAGS_URL:-}" ]; then
  curl -fsSL "$AZURE_SERVICE_TAGS_URL" -o "$DATA/azure.json"
else
  echo "note: AZURE_SERVICE_TAGS_URL not set; Azure addresses will not be flagged" >&2
fi

# Optional network owner and country data (MaxMind GeoLite2, free account and
# licence key required; attribution required when results are shared).
# Configure GeoIP.conf with EditionIDs GeoLite2-ASN GeoLite2-Country, then:
if command -v geoipupdate >/dev/null 2>&1; then
  geoipupdate -d "$DATA"
else
  echo "note: geoipupdate not installed; network owner and country will be empty" >&2
fi
