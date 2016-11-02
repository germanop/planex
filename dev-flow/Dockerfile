FROM xenserver/planex
MAINTAINER {maintainer}

COPY {yum-conf} /etc/yum.conf
RUN mkdir /etc/yum.repos.d.xs
COPY {xs-repo} /etc/yum.repos.d.xs/xs.repo
{yum-custom}

COPY {logging-ini} /etc/mock/logging.ini
COPY {site-defaults-cfg} /etc/mock/site-defaults.cfg
COPY mock-custom /etc/mock/default.cfg

RUN yum update -y

RUN yum install -y sudo
RUN echo '%wheel ALL=(ALL:ALL) ALL' >> /etc/sudoers
RUN echo 'build ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN sed -i.bak 's/^Defaults.*requiretty//g' /etc/sudoers

# install guilt
WORKDIR /tmp
RUN git clone git://repo.or.cz/guilt.git && \
    cd guilt && \
    make && \
    make install && \
    cd .. && \
    rm -R -f guilt

ENV XSDEVHOME=/build/myrepos/{reponame}

{build-deps}