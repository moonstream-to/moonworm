## What is moonworm?

Moonworm is a set of tools that helps you develop/analyze blockchain dapps. Pump your productivity to the Moon.

### Tools:

1. `moonworm watch` -  Tool to monitor and crawl(index) decoded smart contract data. It gets you historic/on going smart contract’s decoded `events` and `transactions`. No sweat, just provide `abi` and smart contract’s address and get stream of data. With this tool you can: analyze  incidents, set up alerting, build datasets, write sniping bots, etc.
2. `moonworm generate-brownie` - Brownie on steroids. Generate python interface and cli for your smart contracts in “one click”, focus on smart contract development, `moonworm` will do the rest. In addition, you will have syntax highlights which will boost your speed on writing tests.

![moonworm](https://user-images.githubusercontent.com/19771534/164013435-74a9e816-74ef-4e05-a7e5-1f7f620896e7.jpg)


1. `moonworm generate` - cli/ python interface generator for pure `web3` library. In case you prefer not to use `brownie`

## Setup:

```bash
pip install moonworm 
```


## Usage:

### `moonworm watch`:

```bash
moonworm watch --abi <Path to abi file> --contract <Contract address> --web3 <Web3 provider url> --start <Start block> --end <End block>    
```

Arguments:

- `--abi/-i ABI`    Path to abi file
- `--contract/-c CONTRACT` Contract address
- `--web3/-w WEB3`    Web3 provider uri
- `--start/-s START`  block to start watching

Optional args:
- `--end/-e END`      block to stop crawling, if not given, crawler will not stop
- `--poa` Flag for `PoA` networks, for example `polygon`
- `--confirmations CONFIRMATIONS`  Number of confirmations to set for watch. (Default 12)
- `--outfile/-o OUTFILE`  `JSONL` file into which to write events and transactions
- `--db`  Use Moonstream database specified by `MOONSTREAM_DB_URI` to get blocks/transactions. If set, need also provide `--network`
- `-network {ethereum,polygon}`Network name that represents models from db. If the `--db` is set, required
- `--only-events` Flag, if set: only watches events. Default=`False`
- `--min-blocks-batch MIN_BLOCKS_BATCH` Minimum number of blocks to batch together. Default=100
- `--max-blocks-batch MAX_BLOCKS_BATCH` Maximum number of blocks to batch together. Default=1000 **Note**: it is used only in `--only-events` mode
- 

### `moonworm generate-brownie`:

```bash
moonworm generate-brownie -p <Path to brownie project> -o <Outdir where file will be generated> -n <Contract name>
```

Arguments:

- `--project/-p PROJECT`  path to brownie project.
- `--outdir/-o OUTDIR` Output directory where files will be generated.
- `--name/-n NAME` Prefix name for generated files

**NOTE**: For better experience put generated files in sub directory of your brownie project. As an example:

1. `cd myBrownieProject`
2. `moonworm generate-brownie -p . -o generated/ -n MyContract` 

      3. Run the generated cli of the contract: `python3 generated/Mycontract.py -h` 

### `moonworm generate`:

```bash
moonworm generate --abi <Path to abi> -o <Outdir> --interface --cli --name <Prefix name for the generated files>
```

Arguments:

- `--abi/-i ABI` Path to contract abi JSON file
- `--outdir/-o OUTDIR` Output directory where files will be generated.
- `--interface` Flag to generate python interface for given smart contract abi
- `-name/-n NAME` Prefix name for generated files
- `--cli` Flag to generate cli for given smart contract abi

 

## FAQ:

- Ser, is it safe to use?

     Yes, it is. moonworm is a code generator that generates code that uses brownie/web3.

- Ok ser, are there examples of usages?

     [moonstream-dao contracts](https://github.com/bugout-dev/dao/tree/main/dao), [lootbox contract](https://github.com/bugout-dev/lootbox/tree/main/lootbox)

- But ser, I don’t write on python

     Javascript version (hardhat) is coming soon
