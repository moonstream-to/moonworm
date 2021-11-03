# Moonworm
Generate command line and a python interface to any Ethereum smart contract

# Installation
### from pip:
`pip install moonworm`

### from github:
`git clone https://github.com/bugout-dev/moonworm.git`

`cd moonworm/`

create virtual env: `python3 -m venv .venv`

activate virtual env: `source .venv/bin/activate`

install: `python3 -m setup.py install`

# Usage
## Requirments:
### In oreder to have ability to deploy/transact smart contracts:
1. Have a ethereum accaunt for testing purposes. Create one with [metamask](https://metamask.io/) if you don't have
2. Have access to ethereum node (to testnet like Ropsten for testing purposes). Create [Infura accaunt](https://infura.io/) account if you don't have, it is free
3. Some ether to use in your account. Use [Ropsten faucet](https://faucet.ropsten.be/) to get some ether in ropsten testnet
 
## Generating cli and python interface:
Make a directory where files will be generated: `mkdir generated`

### To generate interfaces for moonworm [token contracts](https://github.com/bugout-dev/moonworm/tree/main/centipede/fixture/smart_contracts):
**ERC20:** 
```bash 
moonworm generate --cli --interface -o generated/ --name erc20 --abi erc20
```
**ERC721:**
```bash 
moonworm generate --cli --interface -o generated/ --name erc721 --abi erc721
```
### To generate from given contract abi:
```bash 
moonworm generate --cli --interface -o generated/ --name <Give a name> --abi <Path to abi>
```
**Note:** abi should be `.json` file

## Example of interacting with generated files:
1. Generate erc20 token interface as shown above
2. Run `python3 -m generated.erc20_cli -h` to make sure you have generated files correctly
3. Lets deploy : 
    ``` bash 
    python3 -m generated.erc20_cli deploy <Token name> <Token sumbol> <Token owner> --web3 <Http path to client provider> -b generated/erc20_bytecode.bin
    ```
    * `<Token name>` - Name of the token
    * `<Token symbol>` - Symbol of the token
    * `<Token owner>` - Owner of token, who has ability to mint new tokens. Put your address here
    * `<Http path to client provider>` - Path to jrpc client. `https://ropsten.infura.io/v3/YOUR-PROJECT-ID` if you want use infura ropsten
    
    It will ask your account `private key` in order to submit deployment transaction.
    It will deploy contract and give you your contract address if everything goes well
4. Check if conract deployed: 
    ``` bash
    python3 -m generated.erc20_cli call name --web3 <Http path to client provider> -c <Deployed contract address>
    ```
    
   It should print name of token.
5. Lets mint some tokens to your address:
    ``` bash
    python3 -m generated.erc20_cli transact mint <Your address> <Amount of token to mint> --web3 <Http path to client provider> -c <Deployed contract address>
    ```
    
    It will ask your `private key` and confirmation to send transaction.
    
6. Lets transfer some tokens:
    You can send me some tokens:
    ``` bash
    python3 -m generated.erc20_cli transact transfer 0xa75720c500ae1551c08074E5A9849EA92528401D <Amount of token to transfer> --web3 <Http path to client provider> -c <Deployed contract address>
    ```

