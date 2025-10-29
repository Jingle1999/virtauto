import requests
import sys
import os
import datetime

def main():
    base_url = None
    output = None

    # CLI argument parsing
    args = sys.argv
    for i in range(len(args)):
        if args[i] == "--base-url":
            base_url = args[i+1]
        elif args[i] == "--output":
            output = args[i+1]

    if not base_url:
        base_url = "https://www.virtauto.de"
    if not output:
        output = "logs/agent_reports.md"

    os.makedirs(os.path.dirname(output), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.get(base_url, timeout=10)
        status = "OK" if response.status_code == 200 else f"Error {response.status_code}"
    except Exception as e:
        status = f"Failed ({str(e)})"

    log_entry = f"[{timestamp}] Checked {base_url}: {status}\n"
    print(log_entry)

    with open(output, "a", encoding="utf-8") as f:
        f.write(log_entry)

if __name__ == "__main__":
    main()
