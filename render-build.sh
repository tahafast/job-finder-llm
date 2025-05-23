#!/usr/bin/env bash
set -e

# Install dependencies
apt-get update
apt-get install -y wget gnupg2

# Add Google Chrome's official GPG key and repo
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Chrome
apt-get update
apt-get install -y google-chrome-stable 