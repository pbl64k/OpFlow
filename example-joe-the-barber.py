
# Largely equivalent to GPSS example at:
# http://en.wikipedia.org/wiki/GPSS#Sample_code

from opflow import *

customer_num = 0
total_service_times = []
waiting_times = []

def create_customer(sim, gen):
    global customer_num
    customer_num += 1
    return WorkUnit({'start': sim.now, 'work': 0.0})

def collect_customer_data(sim, proc, customer):
    total_service_times.append(sim.now - customer.data['start'])
    waiting_times.append(sim.now - customer.data['start'] - customer.data['work'])

def record_work_done(sim, proc, customer):
    customer.data['work'] += proc.cur_work_time

barbershop = PrcSim()

# Door will no longer admit new customers after eight hours.
door = UniGen(limit = 480.0, mean = 18.0, epsilon = 6.0, \
        gen = create_customer)

chairs = Queue()

joe = UniPrc(mean = 16.0, epsilon = 4.0, xform = record_work_done)

exit = Consumer(xform = collect_customer_data)

door.send_to(chairs)

joe.get_from(chairs)
joe.send_to(exit)

for x in [door, chairs, joe, exit]:
    barbershop.reg(prc = x)

# While no new customers will enter the shop after eight hours,
# simulation will continue if there are still customers being
# served by Joe or waiting in the queue.
barbershop.run(n = 1)

print 'Joe\'s avg. utilization: %.2f%%' % \
        ((joe.work_time / barbershop.now) * 100)
print 'Total customers:', customer_num
print 'Avg. service time:', (sum(total_service_times) / customer_num)
print 'Avg. waiting time:', (sum(waiting_times) / customer_num)

