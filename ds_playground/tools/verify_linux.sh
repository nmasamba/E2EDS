#!/bin/sh
# Inside the throwaway container of `make verify-linux`, as root: install bubblewrap (owner approval,
# 2026-10-12), then run the given command as an unprivileged user, as the sandbox tests require.
set -e
apt-get update -qq
apt-get install -y -qq --no-install-recommends bubblewrap >/dev/null
useradd --create-home dsp
exec setpriv --reuid=dsp --regid=dsp --init-groups env HOME=/home/dsp sh -c "$1"
