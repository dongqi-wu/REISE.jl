from pyreisejl.utility import const, parser
from pyreisejl.utility.converters import pkl_to_csv
from pyreisejl.utility.extract_data import extract_scenario
from pyreisejl.utility.helpers import (
    WrongNumberOfArguments,
    get_scenario,
    insert_in_file,
    sec2hms,
)
from pyreisejl.utility.launchers import get_launcher


def _record_scenario(scenario_id, runtime):
    """Updates execute and scenario list on server after simulation.

    :param str scenario_id: scenario index.
    :param int runtime: runtime of simulation in seconds.
    """
    insert_in_file(const.EXECUTE_LIST, scenario_id, "status", "finished")

    hours, minutes, _ = sec2hms(runtime)
    insert_in_file(
        const.SCENARIO_LIST, scenario_id, "runtime", "%d:%02d" % (hours, minutes)
    )


def _ensure_required_args(args):
    """Check to make sure all necessary arguments are there:
    (start_date, end_date, interval, input_dir)

    :param argparse.Namespace args: command line args
    :raises WrongNumberOfArguments: if not all required args present
    """
    if not (args.start_date and args.end_date and args.interval and args.input_dir):
        err_str = (
            "The following arguments are required: "
            "start-date, end-date, interval, input-dir"
        )
        raise WrongNumberOfArguments(err_str)


def main(args):
    # If using PowerSimData, get scenario info, prepare grid data and update status
    if args.scenario_id:
        scenario_args = get_scenario(args.scenario_id)
        args.start_date = scenario_args[0]
        args.end_date = scenario_args[1]
        args.interval = scenario_args[2]
        args.input_dir = scenario_args[3]
        args.output_dir = const.OUTPUT_DIR

    _ensure_required_args(args)
    pkl_to_csv(args.input_dir)

    if args.scenario_id:
        # Update status in ExecuteList.csv on server
        insert_in_file(const.EXECUTE_LIST, args.scenario_id, "status", "running")

    # launch simulation
    launcher = get_launcher(args.solver)(
        args.start_date,
        args.end_date,
        args.interval,
        args.input_dir,
        threads=args.threads,
        julia_env=args.julia_env,
    )
    runtime = launcher.launch_scenario()

    # If using PowerSimData, record the runtime
    if args.scenario_id:
        _record_scenario(args.scenario_id, runtime)

    if args.extract_data:
        extract_scenario(
            args.input_dir,
            args.start_date,
            args.end_date,
            scenario_id=args.scenario_id,
            output_dir=args.output_dir,
            keep_mat=args.keep_matlab,
        )


if __name__ == "__main__":
    args = parser.parse_call_args()
    try:
        main(args)
    except Exception as ex:
        print(ex)  # sent to redirected stdout/stderr
        if args.scenario_id:
            insert_in_file(const.EXECUTE_LIST, args.scenario_id, "status", "failed")
