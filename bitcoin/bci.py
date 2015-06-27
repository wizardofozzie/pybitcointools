#!/usr/bin/python
from bitcoin.pyspecials import st, by, safe_hexlify, safe_unhexlify
from bitcoin.main import access, multiaccess, slice, sum
import json, re
import random
import sys
try:
    from urllib.request import build_opener
except:
    from urllib2 import build_opener


# Makes a request to a given URL (first arg) and optional params (second arg)
def make_request(*args):
    opener = build_opener()
    opener.addheaders = [('User-agent',
                          'Mozilla/5.0'+str(random.randrange(1000000)))]
    try:
        return st(opener.open(*args).read().strip()) # st returns a string, NOT bytestring
    except Exception as e:
        try:
            p = st(e.read().strip())
        except:
            p = e
        raise Exception(p)


def parse_addr_args(*args):
    # Valid input formats: blockr_unspent([addr1, addr2,addr3])
    #                      blockr_unspent(addr1, addr2, addr3)
    #                      blockr_unspent([addr1, addr2, addr3], network)
    #                      blockr_unspent(addr1, addr2, addr3, network)
    # Where network is 'btc' or 'testnet'
    network = 'btc'
    addr_args = args
    if len(args) >= 1 and args[-1] in ('testnet', 'btc'):
        network = args[-1]
        addr_args = args[:-1]
    if len(addr_args) == 1 and isinstance(addr_args, list):
        addr_args = addr_args[0]

    return network, addr_args


# Gets the unspent outputs of one or more addresses
def bci_unspent(*args, **kwargs):
    api = "?api=%s" % str(kwargs.get("api", None)) if "api" in kwargs else ""
    network, addrs = parse_addr_args(*args)
    u = []
    for a in addrs:
        try:
            data = make_request('https://blockchain.info/unspent?address=%s%s' % (a, api))
        except Exception as e:
            if str(e) == 'No free outputs to spend':
                continue
            else:
                raise Exception(e)
        try:
            jsonobj = json.loads(data)
            for o in jsonobj["unspent_outputs"]:
                h = safe_hexlify(safe_unhexlify(o['tx_hash'])[::-1])
                u.append({
                    "output": h+':'+str(o['tx_output_n']),
                    "value": o['value']
                })
        except:
            raise Exception("Failed to decode data: "+data)
    return u


def blockr_unspent(*args):
    # Valid input formats: blockr_unspent([addr1, addr2,addr3])
    #                      blockr_unspent(addr1, addr2, addr3)
    #                      blockr_unspent([addr1, addr2, addr3], network)
    #                      blockr_unspent(addr1, addr2, addr3, network)
    # Where network is 'btc' or 'testnet'
    network, addr_args = parse_addr_args(*args)

    if network == 'testnet':
        blockr_url = 'https://tbtc.blockr.io/api/v1/address/unspent/'
    elif network == 'btc':
        blockr_url = 'https://btc.blockr.io/api/v1/address/unspent/'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_unspent'.format(network))

    if len(addr_args) == 0:
        return []
    elif isinstance(addr_args[0], list):
        addrs = addr_args[0]
    else:
        addrs = addr_args
    res = make_request(blockr_url+','.join(addrs))
    data = json.loads(res)['data']
    o = []
    if 'unspent' in data:
        data = [data]
    for dat in data:
        for u in dat['unspent']:
            o.append({
                "output": u['tx']+':'+str(u['n']),
                "value": int(u['amount'].replace('.', ''))
            })
    return o


def helloblock_unspent(*args):
    network, addrs = parse_addr_args(*args)
    if network == 'testnet':
        url = 'https://testnet.helloblock.io/v1/addresses/%s/unspents?limit=500&offset=%s'
    elif network == 'btc':
        url = 'https://mainnet.helloblock.io/v1/addresses/%s/unspents?limit=500&offset=%s'
    o = []
    for addr in addrs:
        for offset in xrange(0, 10**9, 500):
            res = make_request(url % (addr, offset))
            data = json.loads(res)["data"]
            if not len(data["unspents"]):
                break
            elif offset:
                sys.stderr.write("Getting more unspents: %d\n" % offset)
            for dat in data["unspents"]:
                o.append({
                    "output": dat["txHash"]+':'+str(dat["index"]),
                    "value": dat["value"],
                })
    return o

def webbtc_unspent(*args):
    return None

unspent_getters = {
    'bci': bci_unspent,
    'blockr': blockr_unspent,
    'webbtc': webbtc_unspent,           #
    'helloblock': helloblock_unspent
}


def unspent(*args, **kwargs):
    """unspent(addr, "btc", source="blockr")"""
    svc = kwargs.get('source', '')
    f = unspent_getters.get(svc, bci_unspent)
    return f(*args)


# Gets the transaction output history of a given set of addresses,
# including whether or not they have been spent
def history(*args):
    # Valid input formats: history([addr1, addr2,addr3], "btc")
    #                      history(addr1, addr2, addr3, "testnet")
    if len(args) == 0:
        return []
    elif len(args) == 2 and isinstance(args[0], list):
        addrs, network = args[0], args[-1]
    elif len(args) > 2:
        addrs, network = args[:-1], args[-1]
    else:
        addrs = args
        network = "btc"

    if network == "testnet":pass
#         txs = []
#         for addr in addrs:
#             data = make_request("http://test.webbtc.com/address/%s" % addr)
#             jsonobj = json.loads(data)
#             txs.extend(jsonobj["transactions"])
#         for txo in txs:
#             for tx in txo.values():pass
    elif network == "btc":
        txs = []
        for addr in addrs:
            offset = 0
            while 1:
                data = make_request(
                    'https://blockchain.info/address/%s?format=json&offset=%s' %
                    (addr, offset))
                try:
                    jsonobj = json.loads(data)
                except:
                    raise Exception("Failed to decode data: "+data)
                txs.extend(jsonobj["txs"])
                if len(jsonobj["txs"]) < 50:
                    break
                offset += 50
                sys.stderr.write("Fetching more transactions... "+str(offset)+'\n')
        outs = {}
        for tx in txs:
            for o in tx["out"]:
                if o['addr'] in addrs:
                    key = str(tx["tx_index"])+':'+str(o["n"])
                    outs[key] = {
                        "address": o["addr"],
                        "value": o["value"],
                        "output": tx["hash"]+':'+str(o["n"]),
                        "block_height": tx.get("block_height", None)
                    }
        for tx in txs:
            for i, inp in enumerate(tx["inputs"]):
                if inp["prev_out"]["addr"] in addrs:
                    key = str(inp["prev_out"]["tx_index"]) + \
                        ':'+str(inp["prev_out"]["n"])
                    if outs.get(key):
                        outs[key]["spend"] = tx["hash"]+':'+str(i)
        return [outs[k] for k in outs]


# Pushes a transaction to the network using https://blockchain.info/pushtx
def bci_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx): tx = safe_hexlify(tx)
    return make_request('https://blockchain.info/pushtx', 'tx='+tx)


def eligius_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx): tx = safe_hexlify(tx)
    s = make_request(
        'http://eligius.st/~wizkid057/newstats/pushtxn.php',
        'transaction='+tx+'&send=Push')
    strings = re.findall('string[^"]*"[^"]*"', s)
    for string in strings:
        quote = re.findall('"[^"]*"', string)[0]
        if len(quote) >= 5:
            return quote[1:-1]


def blockr_pushtx(tx, network='btc'):
    if network == 'testnet':
        blockr_url = 'https://tbtc.blockr.io/api/v1/tx/push'
    elif network == 'btc':
        blockr_url = 'https://btc.blockr.io/api/v1/tx/push'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_pushtx'.format(network))

    if not re.match('^[0-9a-fA-F]*$', tx): tx = safe_hexlify(tx)
    return make_request(blockr_url, '{"hex":"%s"}' % tx)


def helloblock_pushtx(tx):
    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = safe_hexlify(tx)
    return make_request('https://mainnet.helloblock.io/v1/transactions',
                        'rawTxHex='+tx)

def webbtc_pushtx(tx, network='btc'):
    if network == 'testnet':
        webbtc_url = 'http//test.webbtc.com/relay_tx'
    elif network == 'btc':
        webbtc_url = 'https://webbtc.com/relay_tx'
    if not re.match('^[0-9a-fA-F]*$', tx):
        tx = safe_hexlify(tx)
    return make_request(webbtc_url, 'tx='+tx)

pushtx_getters = {
    'bci': bci_pushtx,
    'blockr': blockr_pushtx,
    'webbtc': webbtc_pushtx,        # POST to test.webbtc.com/relay_tx
    'helloblock': helloblock_pushtx
}


def pushtx(*args, **kwargs):
    svc = kwargs.get('source', '')
    f = pushtx_getters.get(svc, bci_pushtx)
    return f(*args)


def last_block_height(network='btc'):
    if network == 'testnet':
        data = make_request('https://tbtc.blockr.io/api/v1/block/info/last')
        jsonobj = json.loads(data)
        return jsonobj["data"]["nb"]
    data = make_request('https://blockchain.info/latestblock')
    jsonobj = json.loads(data)
    return jsonobj["height"]


# Gets a specific transaction
def bci_fetchtx(txhash):
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = safe_hexlify(txhash)
    data = make_request('https://blockchain.info/rawtx/'+txhash+'?format=hex')
    return data


def blockr_fetchtx(txhash, network='btc'):
    if network == 'testnet':
        blockr_url = 'https://tbtc.blockr.io/api/v1/tx/raw/'
    elif network == 'btc':
        blockr_url = 'https://btc.blockr.io/api/v1/tx/raw/'
    else:
        raise Exception(
            'Unsupported network {0} for blockr_fetchtx'.format(network))
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = safe_hexlify(txhash)
    jsondata = json.loads(make_request(blockr_url+txhash))
    return st(jsondata['data']['tx']['hex'])    # added st() to repair unicode return hex strings for python 2


def helloblock_fetchtx(txhash, network='btc'):
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = safe_hexlify(txhash)
    if network == 'testnet':
        url = 'https://testnet.helloblock.io/v1/transactions/'
    elif network == 'btc':
        url = 'https://mainnet.helloblock.io/v1/transactions/'
    else:
        raise Exception(
            'Unsupported network {0} for helloblock_fetchtx'.format(network))
    data = json.loads(make_request(url + txhash))["data"]["transaction"]
    o = {
        "locktime": data["locktime"],
        "version": data["version"],
        "ins": [],
        "outs": []
    }
    for inp in data["inputs"]:
        o["ins"].append({
            "script": inp["scriptSig"],
            "outpoint": {
                "index": inp["prevTxoutIndex"],
                "hash": inp["prevTxHash"],
            },
            "sequence": 4294967295
        })
    for outp in data["outputs"]:
        o["outs"].append({
            "value": outp["value"],
            "script": outp["scriptPubKey"]
        })
    from bitcoin.transaction import serialize
    from bitcoin.transaction import txhash as TXHASH
    tx = serialize(o)
    assert TXHASH(tx) == txhash
    return tx

def webbtc_fetchtx(txhash, network='btc'):
    if network == 'testnet':
        webbtc_url = 'http://test.webbtc.com/tx/'
    elif network == 'btc':
        webbtc_url = 'http://webbtc.com/tx/'
    else:
        raise Exception(
            'Unsupported network {0} for webbtc_fetchtx'.format(network))
    if not re.match('^[0-9a-fA-F]*$', txhash):
        txhash = safe_hexlify(txhash)
    hexdata = make_request(webbtc_url + txhash + ".hex")
    return st(hexdata)

fetchtx_getters = {
    'bci': bci_fetchtx,
    'blockr': blockr_fetchtx,
    'webbtc': webbtc_fetchtx,       #   http://test.webbtc.com/tx/txid.[hex,json, bin]
    'helloblock': helloblock_fetchtx
}


def fetchtx(*args, **kwargs):
    svc = kwargs.get("source", "")
    f = fetchtx_getters.get(svc, bci_fetchtx)
    return f(*args)


def firstbits(address):
    if len(address) >= 25:
        return make_request('https://blockchain.info/q/getfirstbits/'+address)
    else:
        return make_request(
            'https://blockchain.info/q/resolvefirstbits/'+address)


def get_block_at_height(height):
    j = json.loads(st(make_request("https://blockchain.info/block-height/" +
                   str(height)+"?format=json")))
    for b in j['blocks']:
        if b['main_chain'] is True:
            return b
    raise Exception("Block at this height not found")


def _get_block(inp):
    if len(str(inp)) < 64:
        return get_block_at_height(inp)
    else:
        return json.loads(make_request(
                          'https://blockchain.info/rawblock/'+inp))


def get_block_header_data(inp):
    j = _get_block(inp)
    return {
        'version': j['ver'],
        'hash': j['hash'],
        'prevhash': j['prev_block'],
        'timestamp': j['time'],
        'merkle_root': j['mrkl_root'],
        'bits': j['bits'],
        'nonce': j['nonce'],
    }


def get_txs_in_block(inp):
    j = _get_block(inp)
    hashes = [t['hash'] for t in j['tx']]
    return hashes


def get_block_height(txhash):
    j = json.loads(make_request('https://blockchain.info/rawtx/'+txhash))
    return j['block_height']


def get_block_coinbase(txval):
    # TODO: use translation table for coinbase fields
    j = _get_block(inp=txval)
    cb = safe_unhexlify(st(j['tx'][0]['inputs'][0]['script']))
    alpha = set(map(chr, list(range(32, 126))))
    cbtext = ''.join(list(map(chr, filter(lambda x: chr(x) in alpha, bytearray(cb)))))
    return cbtext

#  def rscan(*args, **kwargs):
#      if len(args) == 1 and isinstance(args, str): 
#          addr = args[0]
#      if len(args) == 1 and isinstance(args, list):
#          addrs = args
#     urladdr = 'https://blockchain.info/address/%s?format=json&offset=%s'
#  	
#     addrdata = json.loads(make_request(urladdr % (addr, '0')))
#     ntx = addrdata.get('n_tx', len(addrdata["txs"]))
#     
#     txs = []
#     for i in range(0, ntx//50 + 1):
#         sys.stderr.write("Fetching Txs from offset\t%s\n" % str(i*50))
#         jdata = json.loads(make_request(urladdr % (addr, str(i*50))))
#         txs.extend(jdata["txs"])
#     
#     inputs = multiaccess(txs, "inputs")				# get all Tx inputs
#     ninps = tuple([len(x["inputs"]) for x in txs])	# number of inputs
#     scripts = map(lambda x, y: 
