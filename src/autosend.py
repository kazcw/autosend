#!/usr/bin/python

import os
import simplejson as json
from decimal import Decimal
import copy
import bitcoinrpc.authproxy

import rules

CONFIG_PATH = os.path.expanduser(os.path.join("~", ".autosend", "config.json"))
BITCOIND_CONF = os.path.expanduser(os.path.join("~", ".bitcoin", "bitcoin.conf"))

def get_bitcoin_conf(path=BITCOIND_CONF):
    cfg = {}
    try:
        with open(path, "r") as conf_file:
            for line in conf_file:
                line = line.rstrip().split('=', 1)
                if len(line) != 2:
                    continue
                cfg[line[0]] = line[1]            
    except IOError:
        pass
    return {
        'user': cfg.get('rpcuser', 'bitcoinrpc'),
        'pass': cfg.get('rpcpassword', ''),
        'host': cfg.get('rpcconnect', '127.0.0.1'),
        'port': int(cfg.get('rpcport', 8333)),
    }

class Autosender(object):
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self._bitcoind = None
        self._config = None

    def validate_sending_address(self, addr):
        res = self.bitcoind.validateaddress(addr)
        if not res['isvalid']:
            raise RuntimeError("Invalid address: %s" % addr)
        if not res['ismine']:
            raise RuntimeError("Address is not in your wallet: %s" % addr)

    def validate_address(self, addr):
        if not self.bitcoind.validateaddress(addr)['isvalid']:
            raise RuntimeError("Invalid address: %s" % addr)

    @classmethod
    def validate_proportion(cls, num):
        if num < 0 or num > 1:
            raise RuntimeError("Invalid decimal proportion: %s" % num)

    def create_split(self, args):
        if args.ADDRESS in self.config['rules']:
            raise RuntimeError("A rule already exists for address '%s'."
                    " To redefine it, first delete it." % args.ADDRESS)
        self.validate_sending_address(args.ADDRESS)
        dests = [(a, Decimal(b)) for a, b in
                [x.split(':') for x in args.OUTPUT_PROPORTION]]
        for dest, amt in dests:
            self.validate_address(dest)
            self.validate_proportion(amt)
        if args.fee < 0:
            raise RuntimeError("Negative fee? What are you trying to pull?")
        if args.minimum <= args.fee:
            raise RuntimeError("Minimum balance to execute must be more than the fee!")
        if sum(d[1] for d in dests) != 1:
            raise RuntimeError("Proportions should add to 1!")
        self.bitcoind.setaccount(args.ADDRESS, args.ADDRESS)
        self.config['rules'][args.ADDRESS] = {
            "action": "split",
            "minimum": args.minimum,
            "fee": args.fee,
            "destinations": dests,
        }
        self.save_config()

    def execute(self, args):
        if args.ADDRESS:
            addrs = args.ADDRESS
        else:
            addrs = self.config['rules'].keys()
        for addr in addrs:
            try:
                rule = self.config['rules'][addr]
            except KeyError:
                print("WARNING: No rule defined to send from address %s (skipping)" %
                        (addr))
            else:
                RuleCls = rules.by_name(rule['action'])
                RuleCls(addr, copy.deepcopy(rule)).execute(self.bitcoind)

    def show_rules(self, args):
        for addr, rule in self.config['rules'].iteritems():
            rule = rules.by_name(rule['action'])(addr, copy.deepcopy(rule))
            print(rule.description)

    def delete(self, args):
        try:
            del self.config['rules'][args.ADDRESS]
        except KeyError:
            raise RuntimeError("No rule exists for address '%s'." % args.ADDRESS)
        else:
            self.save_config()

    @property
    def config(self):
        if self._config is None:
            try:
                config_file = open(self.config_path, 'r')
            except IOError:
                self._config = {
                        'rules': {},
                        'bitcoind': get_bitcoin_conf()
                }
            else:
                cfg = json.load(config_file, parse_float=Decimal)
                config_file.close()
                self._config = cfg
        return self._config

    def save_config(self):
        try:
            os.mkdir(os.path.dirname(self.config_path))
        except OSError:
            # already exists
            pass
        with open(self.config_path, 'w') as config_file:
            json.dump(self.config, config_file)

    def set_param(self, args):
        if args.PARAMETER == 'bitcoind.user':
            self.config['bitcoind']['user'] = args.VALUE
        if args.PARAMETER == 'bitcoind.password':
            self.config['bitcoind']['pass'] = args.VALUE
        if args.PARAMETER == 'bitcoind.host':
            self.config['bitcoind']['host'] = args.VALUE
        if args.PARAMETER == 'bitcoind.port':
            self.config['bitcoind']['port'] = int(args.VALUE)
        self.save_config()

    def get_param(self, args):
        if args.PARAMETER == 'bitcoind.user':
            print(self.config['bitcoind']['user'])
        if args.PARAMETER == 'bitcoind.password':
            print(self.config['bitcoind']['pass'])
        if args.PARAMETER == 'bitcoind.host':
            print(self.config['bitcoind']['host'])
        if args.PARAMETER == 'bitcoind.port':
            print(self.config['bitcoind']['port'])

    @property
    def bitcoind(self):
        if self._bitcoind is None:
            user = self.config['bitcoind']['user']
            password = self.config['bitcoind']['pass']
            host = self.config['bitcoind']['host']
            port = self.config['bitcoind']['port']
            rpc = "http://%s:%s@%s:%s" % (user, password, host, port)
            self._bitcoind = bitcoinrpc.authproxy.AuthServiceProxy(rpc)
        return self._bitcoind
