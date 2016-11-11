FROM xenserver/planex
MAINTAINER {maintainer}

RUN yum install -y sudo
RUN echo '%wheel ALL=(ALL:ALL) ALL' >> /etc/sudoers
RUN echo 'build ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers
RUN sed -i.bak 's/^Defaults.*requiretty//g' /etc/sudoers

COPY {tempdir}/yum.conf /etc/yum.conf
RUN mkdir /etc/yum.repos.d.xs
COPY {tempdir}/xs.repo /etc/yum.repos.d.xs/xs.repo
{yum-custom}

RUN yum update -y

COPY {tempdir}/SPECS /SPECS

COPY {tempdir}/logging.ini /etc/mock/logging.ini
COPY {tempdir}/site-defaults.cfg /etc/mock/site-defaults.cfg
COPY {tempdir}/default.cfg /etc/mock/default.cfg

{add-guilt}

ENV XSDEVHOME=/build/myrepos/

{build-deps}