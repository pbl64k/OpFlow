
# Process simulation:
# Almost the same as example-abc-2-seq.py
# Each work unit has to go through three stages, A, B and C.
# Work units may go through stages in any order.
# This reduces average waiting times for work units by about 5%.

from opflow import *

import random

random.seed('reproducible')

sim = PrcSim()

gen = ExpGen(limit = 2000000.0, mean = 180.0, \
        gen = lambda sim, gen: WorkUnit({'created': sim.now, 'work': 0.0, 'a': False, 'b': False, 'c': False}))

q = Queue()

def upd_work(sim, prc, obj):
    obj.data['work'] += prc.cur_work_time

def set_f(n):
    def f(sim, proc, obj):
        upd_work(sim, proc, obj)
        obj.data[n] = True
    return f

proca = LogNormPrc(mean = 120.0, sd = 20.0, \
        pred = lambda x: not x.data['a'], \
        xform = set_f(n = 'a'))
procb = LogNormPrc(mean = 135.0, sd = 5.0, \
        pred = lambda x: not x.data['b'], \
        xform = set_f(n = 'b'))
procc = LogNormPrc(mean = 100.0, sd = 10.0, \
        pred = lambda x: not x.data['c'], \
        xform = set_f(n = 'c'))

procfin = Prc(pred = lambda x: x.data['a'] and x.data['b'] and x.data['c'])

n = 0
wt = 0.0
diag = False

def init(sim):
    global n, wt
    n = 0
    wt = 0.0

def f(sim, cons, obj):
    global n, wt
    if diag:
        print 'Work unit finished, started on', obj.data['created'],
        print 'finished on', cons.sim.now,
        print 'total time', (cons.sim.now - obj.data['created']),
        print 'work time', obj.data['work']
    n += 1
    wt += (cons.sim.now - obj.data['created']) - obj.data['work']

cons = Consumer(xform = f)

gen.send_to(tgt = q)

proca.get_from(src = q)
proca.send_to(tgt = q)

procb.get_from(src = q)
procb.send_to(tgt = q)

procc.get_from(src = q)
procc.send_to(tgt = q)

procfin.get_from(src = q)
procfin.send_to(tgt = cons)

sim.reg(prc = gen)
sim.reg(prc = q)
sim.reg(prc = proca)
sim.reg(prc = procb)
sim.reg(prc = procc)
sim.reg(prc = procfin)
sim.reg(prc = cons)

avgs = []

def fin(sim):
    print 'Current time:', sim.now
    print 'PA working time:', proca.work_time
    print 'PB working time:', procb.work_time
    print 'PC working time:', procc.work_time
    print 'Work units:', n
    print 'Avg waiting time:', wt / n
    print '-' * 40
    avgs.append(wt / n)

sim.run(n = 100, initializer = init, finalizer = fin)

print avgs
mean = sum(avgs) / len(avgs)
print 'mean:', mean
sd = (sum(map(lambda x: (x - mean) ** 2.0, avgs)) / len(avgs)) ** 0.5
print 'stddev:', sd
se = sd / (len(avgs) ** 0.5)
print 'se:', se
ci = 1.96 * se
print '95% CI:', mean - ci, '-', mean + ci

