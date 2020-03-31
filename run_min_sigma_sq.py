import numpy as np
import openmdao.api as om
import dymos as dm
import matplotlib.pyplot as plt
from openmdao.api import Problem, Group, pyOptSparseDriver, DirectSolver

from pandemic import Pandemic

pop_total = 1.0 * 1e6
infected0 = int(0.0005 * pop_total) + 1
ns = 35

p = om.Problem(model=om.Group())

traj = dm.Trajectory()

p.model.add_subsystem('traj', subsys=traj)

phase = dm.Phase(ode_class=Pandemic,
                 transcription=dm.GaussLobatto(num_segments=ns, 
                                               order=3))
p.model.linear_solver = DirectSolver()
phase.set_time_options(fix_initial=True, duration_bounds=(70.0, 301.0), units='d', targets=['sigma_comp.t'])
#phase.set_time_options(fix_initial=True, fix_duration=True, units='d')


ds = 1e-4
phase.add_state('susceptible', fix_initial=True, units='pax', rate_source='sdot', targets=['susceptible'], lower=0.0,
                upper=pop_total, ref=pop_total/2, defect_scaler = ds)
phase.add_state('dead', fix_initial=True, units='pax', rate_source='ddot', targets=['dead'], lower=0.0,
                upper=pop_total, ref=pop_total/2, defect_scaler = ds)
phase.add_state('infected', fix_initial=True, units='pax', rate_source='idot', targets=['infected'], lower=0.0,
                upper=pop_total, ref=pop_total/2, defect_scaler = ds)
phase.add_state('immune', fix_initial=True, units='pax', rate_source='rdot', targets=['immune'], lower=0.0,
                upper=pop_total, ref=pop_total/2, defect_scaler = ds)
phase.add_state('sum_sigma_sq', rate_source='sigma_comp.filtered_timescaled', defect_scaler = ds, fix_initial=True )

#p.driver = om.ScipyOptimizeDriver()

p.driver = pyOptSparseDriver()
p.driver.options['optimizer'] = 'SNOPT'
#p.driver.opt_settings['Major feasibility tolerance'] = 1.0E-8
#p.driver.opt_settings['Major optimality tolerance'] = 1.0E-5
p.driver.opt_settings['iSumm'] = 6

p.driver.declare_coloring()


t_on = 10.0 
t_off = 500.0 # always on afterwards

phase.add_input_parameter('t_on', units='d', targets=['sigma_comp.t_on'], dynamic=False, val=t_on)
phase.add_input_parameter('t_off', units='d', targets=['sigma_comp.t_off'], dynamic=False, val=t_off)


lim = 0.15
phase.add_path_constraint('infected', units='pax', upper=lim * pop_total, ref=lim*pop_total)

phase.add_control('sigma', targets=['sigma_comp.signal'], lower=0.1, upper=0.4, ref=0.4)

phase.add_boundary_constraint('infected', loc='final', upper=2*infected0, ref=infected0)
phase.add_objective('sum_sigma_sq', loc='final', ref=20.0)


traj.add_phase(name='phase0', phase=phase)
p.setup(check=True)

p.set_val('traj.phase0.t_initial', 0)
p.set_val('traj.phase0.t_duration', 300)

p.set_val('traj.phase0.states:susceptible',
          phase.interpolate(ys=[pop_total - infected0, 0], nodes='state_input'))
p.set_val('traj.phase0.states:infected',
          phase.interpolate(ys=[infected0, 0], nodes='state_input'))
p.set_val('traj.phase0.states:immune',
          phase.interpolate(ys=[0, pop_total/2], nodes='state_input'))
p.set_val('traj.phase0.states:dead',
          phase.interpolate(ys=[1, 0], nodes='state_input'))
p.set_val('traj.phase0.states:sum_sigma_sq',
          phase.interpolate(ys=[0.6, 0.6], nodes='state_input'))

p.run_driver()
sim_out = traj.simulate()

t = sim_out.get_val('traj.phase0.timeseries.time')
s = sim_out.get_val('traj.phase0.timeseries.states:susceptible')
i = sim_out.get_val('traj.phase0.timeseries.states:infected')
r = sim_out.get_val('traj.phase0.timeseries.states:immune')
d = sim_out.get_val('traj.phase0.timeseries.states:dead')

bs = sim_out.get_val('traj.phase0.timeseries.states:sum_sigma_sq')


try:
    sigma = sim_out.get_val('traj.phase0.timeseries.controls:sigma')
except:
    try:
        sigma = sim_out.get_val('traj.phase0.timeseries.polynomial_controls:sigma')
    except:
        sigma = np.ones(t.shape) * 0.4


fig = plt.figure(figsize=(10, 5))
plt.subplot(211)
plt.title('mitigation starting t = 10.0')
plt.plot(t, len(t) * [lim], 'k:', linewidth=0.9, label='goal')
plt.plot([t_on,t_on], [0, 1], 'k--', linewidth=0.9)
plt.plot(t, i/pop_total, label='infected')
plt.plot(t, s/pop_total, label='susceptible')
plt.plot(t, r/pop_total, label='recovd/immune')
plt.plot(t, d/pop_total, label='dead')
plt.xlabel('days')
plt.ylabel('pct. pop')
plt.legend(loc=1)

plt.subplot(212)
plt.plot([t_on,t_on], [0, 1], 'k--', linewidth=0.9)
plt.plot(t, sigma, label='$\\sigma$')
plt.legend()
plt.show()