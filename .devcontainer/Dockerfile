FROM mcr.microsoft.com/devcontainers/base:debian

# Rename vscode user to dev (base image has vscode with UID 1000)
RUN usermod -l dev -d /home/dev -m vscode \
    && groupmod -n dev vscode \
    && sed -i 's/vscode/dev/g' /etc/sudoers.d/vscode || true \
    && mv /etc/sudoers.d/vscode /etc/sudoers.d/dev 2>/dev/null || true

# Remove unused zsh/oh-my-zsh (~15MB)
RUN rm -rf /home/*/.oh-my-zsh /root/.oh-my-zsh && apt-get purge -y zsh && apt-get autoremove -y

# Install Python and development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python path
ENV PATH="/home/dev/.local/bin:${PATH}"

USER dev

# Per-user npm prefix on PATH so claude (installed into ~/.npm-global/bin by
# postCreate) resolves. Set as image ENV, not appended to .bashrc: Debian's
# .bashrc returns early for non-interactive shells, so a PATH export there is
# invisible to scripts and cron. ENV applies to every shell.
ENV PATH="/home/dev/.npm-global/bin:${PATH}"

# Force UTF-8 locale so terminals render Unicode glyphs correctly.
RUN echo 'export LANG=C.UTF-8' >> /home/dev/.bashrc
