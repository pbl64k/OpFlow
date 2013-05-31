
import heapq
import math
import random

class SimEvt(object):
    def __init__(self, ts, action):
        assert callable(action)
        self.ts = float(ts)
        self.action = action

    def __cmp__(self, other):
        assert isinstance(other, SimEvt)
        return -1 if self.ts < other.ts else (1 if self.ts > other.ts else 0)

class WorkUnit(object):
    def __init__(self, data = {}):
        self.data = data

    def __str__(self):
        return str(self.data)

class PrcUnit(object):
    def __init__(self):
        self.sim = None

    def attach_to(self, sim):
        assert isinstance(sim, PrcSim)
        self.sim = sim
        return self

    def reset(self):
        return self

class Gen(PrcUnit):
    def __init__(self, limit, next_ts, gen):
        assert float(limit) > 0.0
        assert callable(next_ts)
        assert callable(gen)
        super(Gen, self).__init__()
        self.limit = limit
        self.next_ts = next_ts
        self.gen = gen
        self.tgt = None

    def send_to(self, tgt):
        assert isinstance(tgt, Consumer)
        self.tgt = tgt
        return self

    def next_evt(self):
        evt_ts = self.next_ts(self.sim, self)
        def f(sim):
            self.tgt.accept(self.gen(self.sim, self))
            self.sched_next_evt()
        return SimEvt(evt_ts, f)

    def sched_next_evt(self):
        evt = self.next_evt()
        if evt.ts <= self.limit:
            self.sim.sched(evt)
        return self

    def reset(self):
        self.sched_next_evt()
        return self

class UniGen(Gen):
    def __init__(self, limit, mean, epsilon, gen):
        assert float(limit) > 0.0
        assert float(mean) > 0.0
        assert float(epsilon) >= 0.0
        assert float(mean) >= float(epsilon)
        assert callable(gen)
        self.a = mean - epsilon
        self.b = mean + epsilon
        f = lambda sim, g: sim.now + random.uniform(g.a, g.b)
        super(UniGen, self).__init__(limit, f, gen)

class ExpGen(Gen):
    def __init__(self, limit, mean, gen):
        assert float(limit) > 0.0
        assert float(mean) > 0.0
        assert callable(gen)
        self.lambd = 1.0 / mean
        f = lambda sim, g: sim.now + random.expovariate(g.lambd)
        super(ExpGen, self).__init__(limit, f, gen)

class Consumer(PrcUnit):
    def __init__(self, xform = None):
        assert xform is None or callable(xform)
        super(Consumer, self).__init__()
        self.xform = xform

    def accept(self, obj):
        assert isinstance(obj, WorkUnit)
        if self.xform is not None:
            self.xform(self.sim, self, obj)
        return self

class Queue(Consumer):
    def __init__(self, xform = None):
        assert xform is None or callable(xform)
        super(Queue, self).__init__(xform)
        self.q = []
        self.obs = []

    def reset(self):
        self.q = []
        self.obs = []
        return self

    def accept(self, obj):
        assert isinstance(obj, WorkUnit)
        for i in range(len(self.obs)):
            f, tgt = self.obs[i]
            if f is None or f(obj):
                self.obs.pop(i)
                tgt.accept(obj)
                return self
        self.q.append(obj)
        return self

    def empty(self, pred = None):
        assert pred is None or callable(pred)
        if pred is None:
            return len(self.q) == 0
        else:
            return len(filter(pred, self.q)) == 0

    def dequeue(self, pred = None):
        assert pred is None or callable(pred)
        assert not self.empty()
        if pred is None:
            return self.q.pop(0)
        else:
            for i in range(len(self.q)):
                if pred(self.q[i]):
                    return self.q.pop(i)

    def subscribe(self, tgt, pred = None):
        assert isinstance(tgt, Consumer)
        assert pred is None or callable(pred)
        if not self.empty(pred):
            tgt.accept(self.dequeue(pred))
        else:
            self.obs.append((pred, tgt))
        return self

class Prc(Consumer):
    def __init__(self, pred = None, xform = None, delay = None):
        assert pred is None or callable(pred)
        assert xform is None or callable(xform)
        assert delay is None or callable(delay)
        super(Prc, self).__init__(xform)
        self.pred = pred
        self.delay = (lambda sim, prc, obj: 0.0) if delay is None else delay
        self.src = None
        self.tgt = None
        self.work_time = 0.0
        self.busy = False

    def get_from(self, src):
        assert isinstance(src, Queue)
        self.src = src
        return self

    def send_to(self, tgt):
        assert isinstance(tgt, Consumer)
        self.tgt = tgt
        return self

    def reset(self):
        self.work_time = 0.0
        self.busy = False
        self.src.subscribe(self, self.pred)
        return self

    def accept(self, obj):
        assert isinstance(obj, WorkUnit)
        assert not self.busy
        self.busy = True
        self.cur_work_time = self.delay(self.sim, self, obj)
        cont_ts = self.sim.now + self.cur_work_time
        self.work_time += self.cur_work_time
        super(Prc, self).accept(obj)
        def f(sim):
            self.tgt.accept(obj)
            self.busy = False
            self.src.subscribe(self, self.pred)
        self.sim.sched(SimEvt(cont_ts, f))
        return self

class UniPrc(Prc):
    def __init__(self, mean, epsilon, pred = None, xform = None):
        assert float(mean) >= 0.0
        assert float(epsilon) >= 0.0
        assert float(mean) >= float(epsilon)
        self.a = mean - epsilon
        self.b = mean + epsilon
        delay = lambda sim, prc, obj: random.uniform(prc.a, prc.b)
        super(UniPrc, self).__init__(pred, xform, delay)

class LogNormPrc(Prc):
    def __init__(self, mean, sd, pred = None, xform = None):
        assert float(mean) >= 0.0
        assert float(sd) >= 0.0
        self.mean = mean
        self.sd = sd
        self.sigmasq = math.log(1.0 + (self.sd / self.mean) ** 2.0)
        self.sigma = math.sqrt(self.sigmasq)
        self.mu = math.log(self.mean) - 0.5 * self.sigmasq
        delay = lambda sim, prc, obj: random.lognormvariate(prc.mu, prc.sigma)
        super(LogNormPrc, self).__init__(pred, xform, delay)

class PrcSim(object):
    def __init__(self):
        self.now = 0.0
        self.objs = []
        self.pq = []

    def reg(self, prc):
        assert isinstance(prc, PrcUnit)
        self.objs.append(prc)
        prc.attach_to(self)
        return self

    def sched(self, evt):
        assert isinstance(evt, SimEvt)
        heapq.heappush(self.pq, evt)
        return self

    def proc_evt(self, evt):
        assert isinstance(evt, SimEvt)
        assert evt.ts >= self.now
        self.now = evt.ts
        return evt.action(self)

    def run(self, n = 1, initializer = None, finalizer = None):
        assert int(n) >= 1
        assert initializer is None or callable(initializer)
        assert finalizer is None or callable(finalizer)
        for i in range(n):
            self.now = 0.0
            self.pq = []
            if initializer is not None:
                initializer(self)
            for obj in self.objs:
                obj.reset()
            while len(self.pq) > 0:
                self.proc_evt(heapq.heappop(self.pq))
            if finalizer is not None:
                finalizer(self)
        return self

