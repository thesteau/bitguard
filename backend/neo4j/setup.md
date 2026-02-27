# Setup

## Disk Setup
lsblk
sudo mkfs -t xfs /dev/nvme1n1
sudo mkdir /data
sudo mount /dev/nvme1n1 /data
df -h
sudo blkid
sudo nano /etc/fstab
sudo mount -a


## Install docker
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu

## Neo4j directory setup
mkdir -p /data/neo4j/{data,logs,import,plugins,conf,query}
sudo chown -R ubuntu:ubuntu /data
touch /data/neo4j/docker-compose.yml
touch /data/neo4j/.env

## Download dump
sudo apt install -y awscli
aws sts get-caller-identity

mkdir -p /data/neo4j/import/dump
aws s3 sync s3://210-btc/neo4j_db_dump/ /data/neo4j/import/dump

## Extract
sudo apt install -y p7zip-full
7z x "/data/neo4j/import/dump/neo4j.dump.gz.001" -o"/data/neo4j/import/extract"

## Load into DB
docker run --rm -v /data/neo4j/data:/data -v /data/neo4j/import:/import neo4j:5-enterprise neo4j-admin database load neo4j --from-path=/import/extract --overwrite-destination --verbose

## Run docker compose
docker compose up -d