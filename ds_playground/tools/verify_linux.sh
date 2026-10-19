#!/bin/sh
# Inside the throwaway container of `make verify-linux`, as root: install bubblewrap (owner approval,
# 2026-10-12), then run the given command as an unprivileged user, as the sandbox tests require.
set -e
apt-get update -qq
apt-get install -y -qq --no-install-recommends bubblewrap >/dev/null
useradd --create-home dsp
# `make live-linux`: the compiler for llama.cpp and the build volume as the user's own.
if [ -d /llama ]; then
  apt-get install -y -qq --no-install-recommends build-essential cmake >/dev/null
  chown -R dsp:dsp /build
fi
status=0
setpriv --reuid=dsp --regid=dsp --init-groups env HOME=/home/dsp sh -c "$1" || status=$?
# `make sat-linux` and `make live-linux`: the evidence the run wrote, copied out through the one
# writable mount whatever the run's outcome (a failed run's records are the ones to read).
if [ -d /evidence ] && [ -d /tmp/evidence ]; then cp /tmp/evidence/*.json /evidence/; fi
exit $status
