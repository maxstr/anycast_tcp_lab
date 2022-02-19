FROM ubuntu:focal as binary_builder
RUN apt update
RUN DEBIAN_FRONTEND="noninteractive" apt install -y build-essential pkg-config automake autoconf libxtables-dev libip4tc-dev libip6tc-dev libipset-dev libnl-3-dev libnl-genl-3-dev libssl-dev libnftnl-dev libmnl-dev curl

# Get keepalived
RUN bash -c 'curl https://www.keepalived.org/software/keepalived-2.2.7.tar.gz | tee keepalived-2.2.7.tar.gz | md5sum -c <(echo "5f310b66a043a1fb31acf65af15e95bc  -") && tar xzvf keepalived-2.2.7.tar.gz && cd keepalived-2.2.7 && \
	./configure && \
	make && \
	cp bin/genhash bin/keepalived /'

# Get remco
RUN bash -c 'curl -L https://github.com/HeavyHorst/remco/releases/download/v0.12.1/remco_0.12.1_linux_amd64.zip | gunzip | tee /remco | sha256sum -c <(echo "466a20fe2e1691105aa63e473d672d43f5b8fb21ea645078bd5bee7c23acb33d  -") && chmod +x /remco'

FROM ubuntu:focal as base
RUN apt update
RUN DEBIAN_FRONTEND="noninteractive" apt install -y iproute2 nmap netcat dnsutils curl iputils-* ipvsadm vim tcpdump iptables nftables python3 python3.9-venv python3-pip

FROM base as forwarder
# This is required for the bird2 install
RUN echo 'path-include=/usr/share/doc/bird2/*' > /etc/dpkg/dpkg.cfg.d/include-bird
RUN DEBIAN_FRONTEND="noninteractive" apt install -y bird2

# Keepalived binaries
COPY --from=binary_builder /keepalived /usr/sbin/keepalived
COPY --from=binary_builder /genhash /usr/bin/genhash

# Remco binaries
COPY --from=binary_builder /remco /usr/local/bin/remco

ADD python_modules/vip_sync /opt/vip_sync
WORKDIR /opt/vip_sync
RUN pip3 install -r requirements.txt

# Configs
WORKDIR /remco
ADD forwarder/remco.conf /remco
ADD forwarder/keepalived.tmpl /remco
ADD forwarder/bird.tmpl /remco
ADD forwarder/services.yaml.tmpl /remco


ENTRYPOINT ["/usr/local/bin/remco", "-config", "/remco/remco.conf"]

FROM base as backend
RUN apt install -y python3-nftables python3-yaml nginx

ADD backend/nginx.conf /

ADD python_modules/nftables_sync /opt/nftables_sync

COPY --from=binary_builder /remco /usr/local/bin/remco
WORKDIR /remco
ADD backend/remco.conf /remco
ADD backend/services.yaml.tmpl /remco/services.yaml.tmpl
ADD backend/init.sh /init.sh

ENTRYPOINT ["/usr/local/bin/remco", "-config", "/remco/remco.conf"]

FROM base as client
ADD client/start.sh /start.sh

ENTRYPOINT ["/start.sh"]

FROM base as router
RUN echo 'path-include=/usr/share/doc/bird2/*' > /etc/dpkg/dpkg.cfg.d/include-bird
RUN DEBIAN_FRONTEND="noninteractive"  apt install -yq bird2

ADD router/bird.conf /bird.conf

ENTRYPOINT ["bird", "-fc", "/bird.conf", "-s", "/bird.ctl"]

