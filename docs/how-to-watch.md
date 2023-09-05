# How to `watch`

This is a guide to the `moonworm watch` command, which you can use to gather data about smart contract
usage on public blockchains.

You do not have to click on any of the links in order to understand this guide. They are just there in
case you want to dig deeper after you're done with this document.

## Real use case

This guide will show you how you could actually use `moonworm watch` to analyze the activity of the
Crypto Unicorns NFTs on the Polygon blockchain.

We use Polygon because it is easy to query it without setting up an account anywhere and giving over your
credit card information.

We use Crypto Unicorns because it has a long and varied history of on-chain activity which is interesting
to analyze.

## What you will need

### Access to a node

`moonworm watch` gets information about smart contract activity by connecting to blockchain nodes via
their [JSON-RPC APIs](https://ethereum.org/en/developers/docs/apis/json-rpc/).

All that `moonworm watch` needs in order to do its work is a URL to a JSON-RPC API for the blockchain
you want to crawl data from.

For Polygon, there is a free, public JSON-RPC URL available for anybody to use: https://polygon-rpc.com.

If you want to query some other blockchain, you can set up an account at [QuickNode](https://www.quicknode.com/),
[Infura](https://www.infura.io/), or [Alchemy](https://www.alchemy.com/).

Infura and Alchemy are more generous with their free tiers if you're still in the experimental phases.
QuickNode is the best of the three for data quality. [Read here for more information](https://blog.moonstream.to/2022/08/18/downsides-of-crawling-data-with-infura-and-alchemy/).

### Smart contract address

You will need to know the address of the smart contract that you want to gather data about.

For example, the Crypto Unicorns NFT contract we will be gathering data for in this guide is available
at [`0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f`](https://polygonscan.com/address/0xdc0479cc5bba033b3e7de9f178607150b3abce1f) on the Polygon network.

You can usually find smart contract addresses on the explorer for their blockchains if their developers
have published their source code. Try searching for the contract by name on [Etherscan](https://etherscan.io) or
[Polygonscan](https://polygonscan.com) or [OP Mainnet Explorer](https://optimistic.etherscan.io/) or [BaseScan](https://basescan.org/) or \<insert blockchain explorer for your chain\>.

If you can't find the contract addresses this way, you can find them by interacting with the application
and recording the addresses that you submit transactions through.

<!-- Deployment block: 21425773 -->

### Smart contract ABI

Smart contracts expose interfaces in the form of JSON objects called ABIs, short for "application binary
interfaces".

This repository contains some common ABIs in [`moonworm/fixture/abis/`](../moonworm/fixture/abis/).

We will be using [`OwnableERC721.json`](../moonworm/fixture/abis/OwnableERC721.json) to analyze the NFT
activity of the Crypto Unicorns contract. That particular contract has a lot more functionality than just
the functionality for ERC721. This just shows that the ABI you use need not be exhaustive. You will only
be able to decode activity corresponding to the ABI, though.

### Do you need to set the `--poa` flag?

Networks like Polygon have a slightly different block structure compared to Ethereum mainnet and other
blockchains following its standard. If you call `moonworm watch` to crawl function calls on those chains,
you may run into an error like this:

```
web3.exceptions.ExtraDataLengthError: The field extraData is 97 bytes, but should be 32. It is quite likely that you are connected to a POA chain. Refer to http://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority for more details. The full extraData is: HexBytes('0xd682020983626f7288676f312e31372e32856c696e75780000000000000000008399cafaaf72cdb2dc5ff5a8c93b4af476d066c5cc57edfcc0c5e627b1e7893322634137e72db79744e99ba717031de8614eac7452f2e9b7dc2c3f21c30282f201')
```

If this is the case, you are likely on a chain that requires you to call `moonworm watch` with its `--poa` flag.

This is an immutable property of the blockchain you are working with. For example, on Ethereum mainnet,
you will never have to set `--poa`. And on Polygon, you will always have to set `--poa`.

For more about this, [read the web3.py documentation](https://web3py.readthedocs.io/en/stable/middleware.html#why-is-geth-poa-middleware-necessary).

In the example in this guide, since we are crawling from Polygon, we will be using `--poa`.

### Do you need to set the `--only-events` flag?

`moonworm watch` gives you the ability to crawl function calls to a contract and events emitted by that
contract.

Function calls and events are crawled in different ways, and function calls are much slower to crawl than
event emissions.

Most of the information you want is in the events, and so it is highly recommended to use the `--only-events`
flag for speed of crawling.

If you want to decode transactions sent to a contract in addition to the events emitted by that contract,
leave off the `--only-events` flag.

In the example in thise guide, we will be using `--only-events`.

## Building the Crypto Unicorns NFT activity dataset

First, you should set up your Python environment and install `moonworm` using:

```bash
pip install moonworm[moonstream]
```

Once installed, let us figure out how to invoke `moonworm watch` to construct our dataset:

```bash
moonworm watch -h
```

This should give you output that looks like this:

```
$ moonworm watch -h
usage: moonworm watch [-h] -i ABI -c CONTRACT -w WEB3 [--db] [--network {}] [--start START] [--end END] [--poa] [--confirmations CONFIRMATIONS] [--min-blocks-batch MIN_BLOCKS_BATCH]
                      [--max-blocks-batch MAX_BLOCKS_BATCH] [--batch-size-update-threshold BATCH_SIZE_UPDATE_THRESHOLD] [--only-events] [-o OUTFILE]

options:
  -h, --help            show this help message and exit
  -i ABI, --abi ABI     ABI file path or 'erc20' or 'erc721' or cu
  -c CONTRACT, --contract CONTRACT
                        Contract address
  -w WEB3, --web3 WEB3  Web3 provider
  --db                  Use Moonstream database specified by 'MOONSTREAM_DB_URI' to get blocks/transactions. If set, need also provide --network
  --network {}          Network name that represents models from db. If --db is set, required
  --start START, -s START
                        Block number to start watching from
  --end END, -e END     Block number at which to end watching
  --poa                 Pass this flag if u are using PoA network
  --confirmations CONFIRMATIONS
                        Number of confirmations to wait for. Default=15
  --min-blocks-batch MIN_BLOCKS_BATCH
                        Minimum number of blocks to batch together. Default=100
  --max-blocks-batch MAX_BLOCKS_BATCH
                        Maximum number of blocks to batch together. Default=1000
  --batch-size-update-threshold BATCH_SIZE_UPDATE_THRESHOLD
                        Number of minimum events before updating batch size (only for --only-events mode). Default=100
  --only-events         Only watch events. Default=False
  -o OUTFILE, --outfile OUTFILE
                        Optional JSONL (JsON lines) file into which to write events and method calls
```

We already know that we will be using [`OwnableERC721.json`](../moonworm/fixture/abis/OwnableERC721.json)
as our ABI, so copy that file over to your working directory. I'll assume you have retained the name `OwnableERC721.json`.

We also know:
- `--contract 0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f`
- `--web3 "https://polygon-rpc.com"`
- `--poa`
- `--only-events`

We can ignore `--db`, `--network`, `--confirmations`, `--min-blocks-batch`, `--max-blocks-batch`, `--batch-size-updated-threshold`.
These events are useful if you want to run an ongoing crawl in production, but we are just building
a small dataset as an example that we can play with in this guide.

We need to determine `--start` and `--end`. These are the block number at which our crawl should begin
and the block number at which our crawl should end. We don't need to specify `--end`. If we do not, the
crawl will run forever.

For this example, we will crawl the NFT activity in the first 300,000 blocks after the deployment of
the Crypto Unicorns NFT contract. This roughly corresponds to its first week of activity.

You can find the block at which Crypto Unicorns was deployed by [viewing the contract on Polygonscan](https://polygonscan.com/address/0xdc0479cc5bba033b3e7de9f178607150b3abce1f),
but `moonworm` gives you a nice way to get teh deployment block directly from your command line:

```bash
moonworm find-deployment --web3 "https://polygon-rpc.com" --contract 0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f --interval 0.1
```

This produces the output:

```
$ moonworm find-deployment --web3 "https://polygon-rpc.com" --contract 0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f --interval 0.1
21418707
```

That tells us that the Crypto Unicorns NFT contract was deployed in block 21,418,707. So we will use:
- `--start 21418707`
- `--end 21718707`

We will save the dataset to a file called `cryptounicorns-21418707-21718707.json` and we will use the `--outfile cryptounicorns-21418707-21718707.json` argument
to specify this.

To sum things up, this will be our invocation (it is a multi-line command you can copy and paste into your terminal):

```bash
moonworm watch \
    --abi OwnableERC721.json \
    --contract 0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f \
    --web3 "https://polygon-rpc.com" \
    --poa \
    --only-events \
    --start 21418707 \
    --end 21718707 \
    --outfile cryptounicorns-21418707-21718707.json
```

On my machine, this took approximately 2 minutes and 55 seconds:

```
real    2m55.523s
user    0m21.674s
sys     0m2.795s
```

The resulting file contains one emitted event per line and contains 19,906 events:

```bash
$ wc -l cryptounicorns-21418707-21718707.json
19906 cryptounicorns-21418707-21718707.json
```

Each line is a JSON object of the form:

```
$ tail -n1 cryptounicorns-21418707-21718707.json | jq .
{
  "event": "Transfer",
  "args": {
    "from": "0x8151EBBf408Af21B9c373199bf31fea61e6ED7F1",
    "to": "0x1d1503479F7B0DC767CFF26b2E3d232f2BdDF483",
    "tokenId": 2348
  },
  "address": "0xdC0479CC5BbA033B3e7De9F178607150B3AbCe1f",
  "blockNumber": 21718698,
  "transactionHash": "0x626a25697884c18905642421833e4969802bbae30d9bff5002b749a190aeb7ad",
  "logIndex": 424
}
```

Hopefully this has served to demystify the somewhat intimdating `moonworm watch` command-line tool.

If you have any problems or confusion using `moonworm watch`, please do not hesitate to
[create an issue](https://github.com/moonstream-to/moonworm/issues/new) or let us know how we can help on
[Discord](https://discord.gg/K56VNUQGvA).
