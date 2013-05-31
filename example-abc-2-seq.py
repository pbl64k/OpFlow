
# Process simulation:
# Each work unit has to go through three stages, A, B and C.
# Work units will go through stages strictly in A, then B, then C order.

from opflow import *

import random

random.seed('reproducible')

sim = PrcSim()

gen = ExpGen(limit = 2000000.0, mean = 180.0, \
        gen = lambda sim, gen: WorkUnit({'created': sim.now, 'work': 0.0}))

q1 = Queue()
q2 = Queue()
q3 = Queue()

def upd_work(sim, prc, obj):
    obj.data['work'] += prc.cur_work_time

proca = LogNormPrc(mean = 120.0, sd = 20.0, xform = upd_work)
procb = LogNormPrc(mean = 135.0, sd = 5.0, xform = upd_work)
procc = LogNormPrc(mean = 100.0, sd = 10.0, xform = upd_work)

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
        print 'finished on', sim.now,
        print 'total time', (sim.now - obj.data['created']),
        print 'work time', obj.data['work']
    n += 1
    wt += (sim.now - obj.data['created']) - obj.data['work']

cons = Consumer(xform = f)

gen.send_to(tgt = q1)

proca.get_from(src = q1)
proca.send_to(tgt = q2)

procb.get_from(src = q2)
procb.send_to(tgt = q3)

procc.get_from(src = q3)
procc.send_to(tgt = cons)

sim.reg(prc = gen)
sim.reg(prc = q1)
sim.reg(prc = q2)
sim.reg(prc = q3)
sim.reg(prc = proca)
sim.reg(prc = procb)
sim.reg(prc = procc)
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

