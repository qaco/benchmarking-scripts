#!/bin/sh

echo 2048 > /proc/sys/vm/nr_hugepages
mkdir -p /mnt/hugetlbfs
mount -t hugetlbfs none /mnt/hugetlbfs
chown postfix:postfix /mnt/hugetlbfs
hugeadm --set-recommended-shmmax
