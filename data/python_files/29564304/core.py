import sys
import time
import warnings
# Insert path to libs directory.
from pyho.common.utils import libs_to_path, check_stop_flag
libs_to_path()
from pyho.common.utils import printf
from pyho.common.communication import LocalClientComm, NetworkClientComm
from misc import spawn_workers, parse_worker_addresses
from steps import GeneticOptimization, LevmarOptimization


class HybridOptimizer(object):
    "The hybrid (two-step) optimization engine."
    def __init__(self, evaluator_path=None, local=True, local_workers=None, 
            remote_workers=None, stop_flag=None, unknown_args=None,
            **kwargs):
        self.cc = None  # Client communicator.
        self.stop_flag = stop_flag
        self.extra_args = kwargs
        # Initialize relation with workers.
        if local:
            self.__local_mode(local_workers, unknown_args, evaluator_path)
        else:
            self.__network_mode(remote_workers)

    def __del__(self):
        # Close communicator.
        if self.cc:
            self.cc.close()

    def __local_mode(self, workers, xargs, evaluator_path):
        if evaluator_path is None:
            raise ValueError("You have to specify a path to the evaluator"
                " while running in local mode.")
        printf("Starting optimization with local workers (%d)" % workers)
        # Prepare the ZeroMQ communication layer.
        self.cc = LocalClientComm()

        # Arguments to be passed to evaluator processes.
        evaluator_args = xargs + ["-local-mode", "-local-pull-address",
            self.cc.push_addr, "-local-publish-address", self.cc.sub_addr]
        # Launch worker processes.
        spawn_workers(workers, evaluator_path, evaluator_args)

    def __network_mode(self, workers):
        printf("Starting optimization with network workers")
        if not workers:
            raise RuntimeError("You have to specify a list of remote"
                " worker addresses")
        # Connect to workers with ZeroMQ.
        self.cc = NetworkClientComm(addresses=parse_worker_addresses(workers))

    def __fetch_constraints(self):
        u"Fetch constraints from any worker."
        _sent = False
        while not _sent:
            _sent = self.cc.get_options(0, wait=False)
            if check_stop_flag(self.stop_flag):
                sys.exit(-1)
        resp = self.cc.resp_options(0, wait=True)
        self.no_vars = resp["num_params"]
        self.mins = resp["min_constr"]
        self.maxes = resp["max_constr"]

    def prepare_optimization(self):
        # Wait until (presumably) all workers are awake and ready
        # to avoid unfair distribution of tasks.
        time.sleep(1)
        printf("Waiting for initial connection")
        self.__fetch_constraints()
        printf("Received initial data from workers")

    def run(self):
        self.prepare_optimization()
        args = dict(no_vars=self.no_vars, mins=self.mins, maxes=self.maxes,
            comm=self.cc, stop_flag=self.stop_flag)

        ga_results = self.run_genetic(args, **self.extra_args)
        self.display_info(ga_results)
        lm_results = self.run_levmar(args, ga_results, **self.extra_args)
        self.display_info(lm_results)

        self.save_output(lm_results)

    def run_genetic(self, args, **extra):
        u"Prepare and run genetic step."
        # Translate all additional arguments that are understood in this step.
        ga_args = dict(args)
        if extra["ga_seed"]:
            ga_args["seed"] = extra["ga_seed"]
        if extra["ga_iter"]:
            ga_args["generations"] = extra["ga_iter"]
        if extra["ga_size"]:
            ga_args["size"] = extra["ga_size"]
        if extra["ga_allele"] is not None:
            ga_args["allele"] = extra["ga_allele"]
        # Run genetic algorithm optimization step...
        ga_opt = GeneticOptimization(**ga_args)
        return ga_opt.run()  # Return optimized parameters vector.

    def run_levmar(self, args, start_vector, **extra):
        u"Prepare and run levmar step."
        lm_args = dict(args)
        lm_args["p0"] = start_vector
        if extra["lm_iter"]:
            lm_args["max_iter"] = extra["lm_iter"]
        if extra["lm_central"] is not None:
            lm_args["central"] = extra["lm_central"]
        lm_opt = LevmarOptimization(**lm_args)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            return lm_opt.run()

    def display_info(self, parameters):
        u"Asks evaluator for parameters description and displays it."
        self.cc.get_stats(parameters, "2%d" % id(parameters))
        response = self.cc.resp_stats("2%d" % id(parameters), wait=True)
        printf("Statistics for given parameters:")
        printf(response["stats"])

    def save_output(self, parameters):
        u"Save optimization results"
        self.cc.save_output(parameters, 1)
        response = self.cc.resp_save(1, wait=True)
        if response["status"] == "" and response["files"]:
            print "Saved files: %s" % ', '.join(response["files"])


__all__ = ["HybridOptimizer"]
