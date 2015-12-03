import sim
world = sim.main()
from serializers import write_trial_log_csv_files, write_workers_to_csv_file
write_trial_log_csv_files(world.log, 'same')
write_workers_to_csv_file(world.workers, 'same/workers.csv')

import sim
import exp_settings
world = sim.main(exp_settings.laggy_asymmetry)
from serializers import write_trial_log_csv_files, write_workers_to_csv_file
write_trial_log_csv_files(world.log, 'laggy')
write_workers_to_csv_file(world.workers, 'laggy/workers.csv')

import main
import storage
import trial_plots
s = storage.ExperimentStorage('laggy_asymmetry')
keys = main.main('exp laggy_asymmetry --concurrency Dispatcher --display-plots')
a_trial = s.get(keys[0])
trial_plots.disappointment(a_trial.data)

import matplotlib.pyplot as plt
import main
main.main('exp laggy_asymmetry ')
plt.show()

import matplotlib.pyplot as plt
import main
main.main('exp safe_workers')
plt.show()

import matplotlib.pyplot as plt
import main
main.main('exp default')
plt.show()
