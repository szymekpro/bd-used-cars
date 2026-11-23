#!/usr/bin/env bash
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
mkdir -p certs
cd certs
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 825 -subj "/CN=bigdata-ca" -out ca.pem
openssl genrsa -out server.key 4096
openssl req -new -key server.key -subj "/CN=localhost" -out server.csr
printf 'subjectAltName=DNS:localhost,DNS:mongo,DNS:mongo-private,IP:127.0.0.1\n' > san.ext
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out server.crt -days 825 -sha256 -extfile san.ext
cat server.key server.crt > mongo.pem
rm -f server.csr san.ext server.key server.crt ca.srl
ls -l ca.pem mongo.pem
