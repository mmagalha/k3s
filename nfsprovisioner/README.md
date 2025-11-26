# With Helm

Follow the instructions from the helm chart README.

The tl;dr is
```bash
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner \
-n nfs-provisioner --create-namespace \
nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server=172.31.254.1 \
    --set nfs.path=/mnt/pool01/nas
```    