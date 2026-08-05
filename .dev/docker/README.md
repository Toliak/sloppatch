The dev image that is my own template btw


For podman: 
- assuming that the user has at least 64k subuids and subgids 
- the image supports rootless podman in rootless podman

Testing:
- In container: `podman image ls` (must show host images with RO=true)
- In container: `podman run --uidmap 0:0:1500 --uidmap 65534:1500:2 -it debian:trixie` and `apt-get update -y`
- on host: `docker pull quay.io/podman/stable`. Then in container: `podman run -v /proc:/proc -it --uidmap 1000:0:1 --uidmap 0:1:1000 --uidmap 1001:1001:20000 --uidmap 65534:22000:2 quay.io/podman/stable`. And something like `yum install vim` inside.


