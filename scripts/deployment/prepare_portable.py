import os
import sys
import argparse

ENV_FILE = ".env"

TEMPLATE = "ALLOWED_HOSTS="

def ensure_allowed_hosts(ip: str):
    if not os.path.exists(ENV_FILE):
        return 1
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith("ALLOWED_HOSTS="):
            found = True
            val = line.split("=", 1)[1].strip()
            # normalize
            hosts = [h.strip() for h in val.split(",") if h.strip()]
            if ip not in hosts:
                hosts.append(ip)
            lines[i] = TEMPLATE + ",".join(hosts)
            break

    if not found:
        lines.append(TEMPLATE + ip)

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    args = parser.parse_args()
    rc = ensure_allowed_hosts(args.ip)
    sys.exit(rc)


if __name__ == "__main__":
    main()
