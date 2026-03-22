#!/usr/bin/env bash
set -e

# Start sshd
/usr/sbin/sshd

# Wait for sshd to be ready
for i in $(seq 1 30); do
    if ssh -o ConnectTimeout=1 root@localhost true 2>/dev/null; then
        break
    fi
    sleep 0.2
done

# Run the command passed to the container
exec "$@"
