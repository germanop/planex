#!/bin/sh

set -xe

echo $@
EXTUID=`stat -c %u /build`
EXTGID=`stat -c %g /build`

# Create 'build' user in the container to match the owner of the
# build directory, so that built packages will have the correct
# owner outside the container.
groupmod build --gid $EXTGID      \
               --non-unique
usermod build --groups mock,wheel \
              --uid $EXTUID       \
              --gid $EXTGID       \
              -d ${XSDEVHOME:-/build} \
              --non-unique

if [ -n "$DEVTOOLS" ]; then
    passwd -l build
    echo 'build ALL=(ALL:ALL) NOPASSWD:ALL' > /etc/sudoers.d/build
    chmod 440 /etc/sudoers.d/build
    chown root:root /etc/sudoers.d/build
    sed -i.bak 's/^Defaults.*requiretty//g' /etc/sudoers
fi

if [ -z "$1" ]; then
    exec su - build
else
    exec su - build -c "$@"
fi
