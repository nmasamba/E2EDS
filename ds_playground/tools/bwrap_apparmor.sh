#!/bin/sh
# CI's ubuntu-24.04: AppArmor refuses unprivileged user namespaces unless a profile allows them, so
# bubblewrap cannot build the sandbox. Allow them for /usr/bin/bwrap alone, as Ubuntu's own profiles
# do for the programs that need them, then prove it with the smallest sandbox bubblewrap can make.
set -e
if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null)" = 1 ]; then
  printf 'abi <abi/4.0>,\ninclude <tunables/global>\nprofile bwrap /usr/bin/bwrap flags=(unconfined) {\n  userns,\n}\n' \
    | sudo tee /etc/apparmor.d/bwrap >/dev/null
  sudo apparmor_parser -r /etc/apparmor.d/bwrap
fi
bwrap --unshare-all --die-with-parent --ro-bind / / true
echo "bubblewrap builds a sandbox here"
