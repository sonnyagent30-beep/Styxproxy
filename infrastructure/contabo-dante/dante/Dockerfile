FROM alpine:3.20

# Install dante-server
RUN apk add --no-cache dante-server curl bash busybox-extras

RUN mkdir -p /etc/dante /default /var/log/dante

# PAM is needed for SOCKS5 username/password auth
RUN apk add --no-cache linux-pam 2>&1 | tail -1

# Custom PAM service for sockd - reads /etc/dante/danted.shadow using pam_pwdfile
# This keeps proxy users isolated from system /etc/shadow
COPY sockd.pam /etc/pam.d/sockd

COPY sockd.conf /default/sockd.conf
RUN ln -sf /etc/dante/sockd.conf /etc/sockd.conf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 1080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD nc -z localhost 1080 || exit 1

# Run as root so we can write to all the files we mount
USER root

CMD ["/usr/local/bin/entrypoint.sh"]
