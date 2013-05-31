
from opflow import *

sim = PrcSim()

gen = ExpGen(limit = 100000.0, mean = 8.0, \
		gen = lambda sim, gen: WorkUnit({'created': gen.sim.now, 'work': 0.0}))

q = Queue()

def upd_work(sim, proc, obj):
    obj.data['work'] += proc.cur_work_time

proca = LogNormPrc(mean = 15.0, sd = 2.5, xform = upd_work)
procb = LogNormPrc(mean = 15.0, sd = 5, xform = upd_work)
procc = LogNormPrc(mean = 30.0, sd = 5, xform = upd_work)

def f(sim, cons, obj):
    print 'Work unit finished, started on', obj.data['created'],
    print 'finished on', sim.now,
    print 'total time', (sim.now - obj.data['created']),
    print 'work time', obj.data['work']

cons = Consumer(xform = f)

gen.send_to(tgt = q)

proca.get_from(src = q)
proca.send_to(tgt = cons)

procb.get_from(src = q)
procb.send_to(tgt = cons)

procc.get_from(src = q)
procc.send_to(tgt = cons)

sim.reg(prc = gen)
sim.reg(prc = q)
sim.reg(prc = proca)
sim.reg(prc = procb)
sim.reg(prc = procc)
sim.reg(prc = cons)

def fin(sim):
	print 'Current time:', sim.now
	print 'PA working time:', proca.work_time
	print 'PB working time:', procb.work_time
	print 'PC working time:', procc.work_time

sim.run(n = 1, initializer = None, finalizer = fin)

