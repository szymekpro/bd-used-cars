FROM apache/hadoop:3.3.6
USER root
RUN sed -i 's|^mirrorlist=|#mirrorlist=|; s|^#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|' /etc/yum.repos.d/CentOS-*.repo \
    && yum install -y python3 \
    && yum clean all \
    && mkdir -p /data/namenode /data/datanode \
    && chown -R hadoop:users /data
USER hadoop
