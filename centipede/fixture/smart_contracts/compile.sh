#!/usr/bin/env sh
#shitty bash code that compiles smart contract with solc
#and puts bytecode to ../bytecodes and abi to ../abis folder
tempdir=".temp"
mkdir $tempdir
solc --abi --bin $1 -o "$tempdir"
filename=${1%.*}
cp "$tempdir/$filename.bin" "../bytecodes/$filename"
cp "$tempdir/$filename.abi" "../abis/$filename.json"
rm $tempdir -r