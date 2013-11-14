from decimal import Decimal

class Rule(object):
    def __init__(self, addr, params):
        self.addr = addr
        self.params = params

    def execute(self, bitcoind):
        raise NotImplementedError()

class Split(Rule):
    def execute(self, bitcoind):
        balance = Decimal(bitcoind.getbalance(self.addr))
        minimum = self.params['minimum']
        if balance < minimum:
            print("%s: SKIPPING: balance of %f below execution balance of %f" %
                    (self.addr, balance, minimum))
            return
        balance -= self.params['fee']
        sends = dict((addr, float(prop*balance)) for addr, prop in self.params['destinations'])
        bitcoind.sendmany(self.addr, sends)
        print("%s: EXECUTING: splitting %s BTC" % (self.addr, balance))

    @property
    def description(self):
        dests = " ".join(":".join((d, str(p))) for d, p in self.params['destinations'])
        return "split %s %s" % (self.addr, dests)

def by_name(name):
    return {
            "split": Split,
    }[name]
