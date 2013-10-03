import random, os, json, sys

from main import *
from transaction import *

argv = sys.argv + ['y']*8

if argv[1] == 'y':
    print "Starting ECC arithmetic tests"
for i in range(8 if argv[1] == 'y' else 0):
    print "### Round %d" % (i+1)
    x,y = random.randrange(2**512) - 2**511, random.randrange(2**512) - 2**511
    print multiply(multiply(G,x),y)[0] == multiply(multiply(G,y),x)[0]
    print add(multiply(G,x),multiply(G,y))[0] == multiply(G,add(x,y))[0]
    hx, hy = encode(x%N,16,64), encode(y%N,16,64)
    print multiply(multiply(G,hx),hy)[0] == multiply(multiply(G,hy),hx)[0]
    print add(multiply(G,hx),multiply(G,hy))[0] == multiply(G,add(hx,hy))[0]
    h1601 = b58check_to_hex(pub_to_addr(priv_to_pub(x)))
    h1602 = b58check_to_hex(pub_to_addr(multiply(G,hx),23))
    print h1601 == h1602
    p = priv_to_pub(sha256(str(x)))
    if i%2 == 1: p = changebase(p,16,256)
    print decompress(compress(p)) == p

if argv[2] == 'y':
    print "Starting Electrum tests"
    for i in range(3):
        seed = sha256(str(random.randrange(2**40)))[:32]
        mpk = electrum_mpk(seed)
        print 'seed: ',seed
        print 'mpk: ',mpk
        for i in range(5):
            pk = electrum_privkey(seed,i)
            pub = electrum_pubkey((mpk,seed)[i%2],i)
            pub2 = priv_to_pub(pk)
            print 'priv: ',pk
            print 'pub: ',pub
            print pub == pub2
            if pub != pub2: print 'DOES NOT MATCH!!!!\npub2: '+pub2

if argv[3] == 'y':
    # Requires Electrum
    wallet = "/tmp/tempwallet_"+str(random.randrange(2**40))
    print "Starting wallet tests with: "+wallet
    os.popen('echo "\n\n\n\n\n\n" | electrum -w %s create' % wallet).read()
    addies = json.loads(os.popen("electrum -w %s listaddresses" % wallet).read())

for i in range(8 if argv[3] == 'y' else 0):
    print "Electrum-style signing and verification tests, against actual Electrum"
    alphabet = "1234567890qwertyuiopasdfghjklzxcvbnm"
    msg = ''.join([random.choice(alphabet) for i in range(random.randrange(20,200))])
    addy = random.choice(addies)
    wif = os.popen('electrum -w %s dumpprivkey %s' % (wallet, addy)).readlines()[-1].strip()
    priv = b58check_to_hex(wif)
    pub = priv_to_pub(priv)

    sig = os.popen('electrum -w %s signmessage %s %s' % (wallet, addy, msg)).readlines()[-1].strip()
    verified = ecdsa_verify(msg,sig,pub)
    print "Verified" if verified else "Verification error"
    rec = ecdsa_recover(msg,sig)
    if pub == rec: print "Recovery successful"
    if pub != rec or not verified:
        print "msg: "+msg
        print "sig: "+sig
        print "priv: "+priv
        print "addy: "+addy
    if pub != rec:
        print "Recovery error"
        print "original  pub: "+pub, hex_to_point(pub)[1]
        print "recovered pub: "+rec

    mysig = ecdsa_sign(msg,priv)
    v = os.popen('electrum -w %s verifymessage %s %s %s' % (wallet,addy, sig, msg)).read()
    print v

for i in range(10 if argv[4] == 'y' else 0):
    print "Transaction-style signing and verification tests"
    alphabet = "1234567890qwertyuiopasdfghjklzxcvbnm"
    msg = ''.join([random.choice(alphabet) for i in range(random.randrange(20,200))])
    priv = sha256(str(random.randrange(2**256)))
    pub = priv_to_pub(priv)
    sig = ecdsa_tx_sign(msg,priv)
    v = ecdsa_tx_verify(msg,sig,pub)
    print "Verified" if v else "Verification error"
    rec = ecdsa_tx_recover(msg,sig)
    print "Recovered" if pub in rec else "Recovery failed"

if argv[5] == 'y':
    tx = '0100000001239f932c780e517015842f3b02ff765fba97f9f63f9f1bc718b686a56ed9c73400000000fd5d010047304402200c40fa58d3f6d5537a343cf9c8d13bc7470baf1d13867e0de3e535cd6b4354c802200f2b48f67494835b060d0b2ff85657d2ba2d9ea4e697888c8cb580e8658183a801483045022056f488c59849a4259e7cef70fe5d6d53a4bd1c59a195b0577bd81cb76044beca022100a735b319fa66af7b178fc719b93f905961ef4d4446deca8757a90de2106dd98a014cc95241046c7d87fd72caeab48e937f2feca9e9a4bd77f0eff4ebb2dbbb9855c023e334e188d32aaec4632ea4cbc575c037d8101aec73d029236e7b1c2380f3e4ad7edced41046fd41cddf3bbda33a240b417a825cc46555949917c7ccf64c59f42fd8dfe95f34fae3b09ed279c8c5b3530510e8cca6230791102eef9961d895e8db54af0563c410488d618b988efd2511fc1f9c03f11c210808852b07fe46128c1a6b1155aa22cdf4b6802460ba593db2d11c7e6cbe19cedef76b7bcabd05d26fd97f4c5a59b225053aeffffffff0310270000000000001976a914a89733100315c37d228a529853af341a9d290a4588ac409c00000000000017a9142b56f9a4009d9ff99b8f97bea4455cd71135f5dd87409c00000000000017a9142b56f9a4009d9ff99b8f97bea4455cd71135f5dd8700000000'
    print "Serialize roundtrip success" if serialize(deserialize(tx)) == tx else "Serialize roundtrip failed"
if argv[6] == 'y':
    script = '47304402200c40fa58d3f6d5537a343cf9c8d13bc7470baf1d13867e0de3e535cd6b4354c802200f2b48f67494835b060d0b2ff85657d2ba2d9ea4e697888c8cb580e8658183a801483045022056f488c59849a4259e7cef70fe5d6d53a4bd1c59a195b0577bd81cb76044beca022100a735b319fa66af7b178fc719b93f905961ef4d4446deca8757a90de2106dd98a014cc95241046c7d87fd72caeab48e937f2feca9e9a4bd77f0eff4ebb2dbbb9855c023e334e188d32aaec4632ea4cbc575c037d8101aec73d029236e7b1c2380f3e4ad7edced41046fd41cddf3bbda33a240b417a825cc46555949917c7ccf64c59f42fd8dfe95f34fae3b09ed279c8c5b3530510e8cca6230791102eef9961d895e8db54af0563c410488d618b988efd2511fc1f9c03f11c210808852b07fe46128c1a6b1155aa22cdf4b6802460ba593db2d11c7e6cbe19cedef76b7bcabd05d26fd97f4c5a59b225053ae'
    print "Script serialize roundtrip success" if serialize_script(deserialize_script(script)) == script else "Script serialize roundtrip failed"

if argv[7] == 'y':
    print "Attempting transaction creation"
    privs = [sha256(str(random.randrange(2**256))) for x in range(4)]
    pubs = [priv_to_pub(priv) for priv in privs]
    addresses = [pub_to_addr(pub) for pub in pubs]
    mscript = mk_multisig_script(pubs[1:],2,3)
    msigaddr = scriptaddr(mscript)
    tx = mktx(['01'*32+':1','23'*32+':2'],[msigaddr+':20202',addresses[0]+':40404'])
    tx1 = sign(tx,1,privs[0])
    sig1 = multisign(tx,0,mscript,privs[1])
    print "Verifying sig1:",verify_tx_input(tx1,0,mscript,sig1,pubs[1])
    sig3 = multisign(tx,0,mscript,privs[3])
    print "Verifying sig3:",verify_tx_input(tx1,0,mscript,sig3,pubs[3])
    tx2 = apply_multisignatures(tx1,0,mscript,[sig1,sig3])
    print "Outputting transaction: ",tx2

if argv[8] == 'y':
    # Created with python-ecdsa 0.9
    # Code to make your own vectors:
    # class gen:
    #     def order(self): return return 115792089237316195423570985008687907852837564279074904382605163141518161494337
    # dummy = gen()
    # for i in range(10): ecdsa.rfc6979.generate_k(dummy,i,hashlib.sha256,hashlib.sha256(str(i)).digest())
    test_vectors = [32783320859482229023646250050688645858316445811207841524283044428614360139869L, 109592113955144883013243055602231029997040992035200230706187150761552110229971L, 65765393578006003630736298397268097590176526363988568884298609868706232621488L, 85563144787585457107933685459469453513056530050186673491900346620874099325918L, 99829559501561741463404068005537785834525504175465914981205926165214632019533L, 7755945018790142325513649272940177083855222863968691658328003977498047013576L, 81516639518483202269820502976089105897400159721845694286620077204726637043798L, 52824159213002398817852821148973968315579759063230697131029801896913602807019L, 44033460667645047622273556650595158811264350043302911918907282441675680538675L, 32396602643737403620316035551493791485834117358805817054817536312402837398361L]
    print "Beginning RFC6979 deterministic signing tests"
    for i in range(10):
        ti = test_vectors[i] 
        mine = deterministic_generate_k(bin_sha256(str(i)),encode(i,256,32))
        if ti == mine:
            print "Test vector matches"
        else:
            print "Test vector does not match"
            print ti
            print mine
