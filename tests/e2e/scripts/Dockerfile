FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tmux openssh-server openssh-client \
    iproute2 procps \
    && rm -rf /var/lib/apt/lists/*

# sshd setup
RUN mkdir -p /run/sshd && ssh-keygen -A

# SSH key pair (no passphrase)
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh \
    && ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N "" \
    && cp /root/.ssh/id_ed25519.pub /root/.ssh/authorized_keys \
    && chmod 600 /root/.ssh/authorized_keys

# Permissive sshd config for testing
RUN printf '%s\n' \
    'PermitRootLogin yes' \
    'PasswordAuthentication no' \
    'StrictModes no' \
    'GatewayPorts yes' \
    'AllowTcpForwarding yes' \
    >> /etc/ssh/sshd_config

# SSH client config — no host key prompts
RUN printf '%s\n' \
    'Host localhost' \
    '    StrictHostKeyChecking no' \
    '    UserKnownHostsFile /dev/null' \
    '    IdentityFile /root/.ssh/id_ed25519' \
    '    LogLevel ERROR' \
    > /root/.ssh/config \
    && chmod 600 /root/.ssh/config

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir pytest pytest-asyncio pytest-timeout

COPY tests/e2e/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["pytest", "tests/e2e/", "-v", "--tb=short"]
