#!/usr/bin/env sh
#shitty script that compiles smart contract with solc
#and puts bytecode to ../bytecodes and abi to ../abis folder
tempdir="$(mktemp -d)"
solc --abi --bin $1 -o "$tempdir"  --optimize --optimize-runs 200
filename=${1%.*}
cp "$tempdir/$filename.bin" "../bytecodes/"
cp "$tempdir/$filename.abi" "../abis/$filename.json"
rm $tempdir -r