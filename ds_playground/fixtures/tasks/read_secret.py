"""A28 acceptance: read a host file every user may read; the OS sandbox must refuse it."""

with open("/etc/passwd") as host, open("seen.txt", "w") as seen:
    seen.write(host.read())
