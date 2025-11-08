#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Installing System-Wide Node.js v20.x ---"

# 1. Install prerequisites
apt-get update
apt-get install -y ca-certificates curl gnupg

# 2. Add the NodeSource repository GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg

# 3. Add the NodeSource repository for Node.js v20
NODE_MAJOR=20
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

# 4. Update package lists again and install Node.js
apt-get update
apt-get install nodejs -y

echo "--- System-wide Node.js installation complete ---"
echo "Verifying versions:"

# These commands will now work for ANY user because node and npx
# are installed in /usr/bin/ which is in everyone's default PATH.
node -v
npm -v
npx -v