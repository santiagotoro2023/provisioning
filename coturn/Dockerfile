FROM coturn/coturn:4.6

# The upstream image's own Dockerfile (coturn/coturn, docker/coturn/*/Dockerfile)
# ends with `USER nobody:nogroup` - a deliberate security choice (a
# network-facing TURN relay dropping root) worth keeping, not undoing. But
# that means COPY below creates /entrypoint.sh owned by root (Docker's own
# default COPY behavior, regardless of the current USER), and a later `RUN
# chmod` would then run AS nobody, which can't chmod a file it doesn't own -
# confirmed live as the actual cause of a real "Operation not permitted"
# build failure on the very first real install test. USER root here, only
# for these two build steps, then back to nobody:nogroup before ENTRYPOINT -
# not a permanent privilege change, and turnserver itself already has
# CAP_NET_BIND_SERVICE set on the binary (via the base image's own setcap),
# so it needs no root at runtime for anything this setup does.
USER root
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
USER nobody:nogroup

ENTRYPOINT ["/entrypoint.sh"]
