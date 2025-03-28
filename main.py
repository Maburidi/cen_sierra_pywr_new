import os
import json
import argparse
from itertools import product
from functools import partial

from sierra.run_basin_model import run_model

import pandas as pd
from loguru import logger
from datetime import date
#from dotenv import load_dotenv
#load_dotenv()



parser = argparse.ArgumentParser()
parser.add_argument("-b", "--basin", help="Basin to run ['stanislaus', 'tuolumne', 'merced', 'upper_san_joaquin', 'all']", default='upper_san_joaquin')
#parser.add_argument("-d", "--debug", help="Debug", action='store_true')
parser.add_argument("-d", "--debug", help="Debug",  type=int, choices=[0, 1], default=0)
parser.add_argument("-mp", "--multiprocessing", help="Multiprocessing protocol (omit for none)", default=None)
parser.add_argument("-c", "--num_cores", help="Number of cores to use in joblib multiprocessing", type=int)
#parser.add_argument("-p", "--include_planning", help="Include planning model", action='store_true')
parser.add_argument("-p", "--include_planning", help="Include planning model", type=int, choices=[0, 1], default=0)
parser.add_argument("-m", "--planning_months", help="Planning months", type=int, default=8)
parser.add_argument("-bl", "--blocks", help="Number of piecewise blocks", type=int, default=5)
parser.add_argument("-sc", "--scenario_set", help="Scenario set")
parser.add_argument("-s", "--start_year", help="Start year", type=int)
parser.add_argument("-e", "--end_year", help="End year", type=int)
parser.add_argument("-y", "--years", help="Years to run (useful for debugging)", type=int)
parser.add_argument("-n", "--run_name", help="Run name")
parser.add_argument("-pb", "--progress_bar", help="Show progress bar", action='store_true')
parser.add_argument("-ns", "--no_suffix", help="Suppress file date suffix in output", action='store_true')
parser.add_argument("--data_path", help="Path to the data directory", default='/content/cen_sierra_pywr_new/data/') 
parser.add_argument("-gm", "--gcm_model", help="set the GCM model name if running gcms", default=None)
parser.add_argument("-lgm", "--lgcm_model", help="set the LOCA2 GCM model name if running gcms", default=None)


#parser.add_argument("--logs_dir", help="Path to the logs directory",
#                    default='/content/drive/MyDrive/Colab_Notebooks/PostDoc_Project1_Pywr/Proj1/cen_sierra_model/logs')
args = parser.parse_args()

#args = get_args()

basin = args.basin
debug = args.debug

include_planning = args.include_planning
multiprocessing = args.multiprocessing
data_path = args.data_path


start = None
end = None
scenarios = []

run_name = args.run_name or 'baseline'

climate_sets = {
    'historical': ['Livneh']
}

planning_months = args.planning_months


if debug:
    start = '{}-10-01'.format(args.start_year or 2000)
    end = '{}-09-30'.format(args.end_year or 2002)

    if not args.run_name:
        run_name = 'development'

else:
    start = '{}-10-01'.format(args.start_year or 2051)
    end = '{}-09-30'.format(args.end_year or 2012)


if args.scenario_set:
    scenario_sets_dir = os.path.join(data_path, 'metadata', 'scenario_sets.json')
    with open(scenario_sets_dir) as f:
        scenario_sets = json.load(f)

    scenario_set_definition = scenario_sets.get(args.scenario_set)
    if not scenario_set_definition:
        raise Exception("Scenario set {} not defined in scenario_sets.json".format(args.scenario_set))
    scenarios = scenario_set_definition.get('scenarios', [])
    climates = scenario_set_definition.get('climates', [])
    run_name = scenario_set_definition['name']
    if climates:
        climate_sets = {}
        if 'historical' in climates:
            climate_sets['historical'] = ['Livneh']
        if 'gcms' in climates:
            gcm_rcps = scenario_set_definition.get('gcms')
            if not gcm_rcps:
                full_basin_name = basin.replace(' ', '_').title() + '_River'
                basin_gcm_hydrology_path = os.path.join(data_path, full_basin_name, 'hydrology', 'gcms')
                basin_gcm_rcps = os.listdir(basin_gcm_hydrology_path)
                gcm_rcps = basin_gcm_rcps
                                
            #if debug:
            #    gcm_rcps = [str(args.gcm_model)]  # Just do 2 gcm_rcps for debugging
            
            if args.gcm_model in gcm_rcps: 
                climate_sets['gcms'] = [str(args.gcm_model)]
            else:
                logger.info(f"'{args.gcm_model}' is not in gcm_rcps")
        
        if 'loca2_gcms' in climates:
            loca2_gcm_rcps = scenario_set_definition.get('loca2_gcms')
            if not loca2_gcm_rcps:
                full_basin_name = basin.replace(' ', '_').title() + '_River'
                loca2_basin_gcm_hydrology_path = os.path.join(data_path, full_basin_name, 'hydrology', 'LOCA2_gcms')
                loca2_basin_gcm_rcps = os.listdir(loca2_basin_gcm_hydrology_path)
                loca2_gcm_rcps = loca2_basin_gcm_rcps
                                
            #if debug:
            #    gcm_rcps = [str(args.gcm_model)]  # Just do 2 gcm_rcps for debugging
            
            if args.lgcm_model in loca2_gcm_rcps: 
                climate_sets['LOCA2_gcms'] = [str(args.lgcm_model)]
            else:
                logger.info(f"'{args.gcm_model}' is not in gcm_rcps")
  

        if 'sequences' in climates:
            sequences_file = os.path.join(data_path, 'metadata/sequence_definitions.csv')
            climate_sets['sequences'] = pd.read_csv(sequences_file, index_col=0, header=0).index



climate_scenarios = []
for climate_set, climates in climate_sets.items():
    climate_scenarios.extend(['{}/{}'.format(climate_set, climate) for climate in climates])


if basin == 'all':
    basins = ['stanislaus', 'tuolumne', 'merced', 'upper_san_joaquin']
    include_planning = True
else:
    basins = [basin]


model_args = list(product(climate_scenarios, basins))


kwargs = dict(
    run_name=run_name,
    include_planning=include_planning,
    debug=debug,
    blocks=args.blocks,
    planning_months=planning_months,
    use_multiprocessing=multiprocessing is not None,
    start=start,
    end=end,
    years=args.years,
    data_path=data_path,
    scenarios=scenarios,
    show_progress=args.progress_bar,
    file_suffix=None if debug or args.no_suffix else date.today().strftime('%Y-%m-%d')
)



if not multiprocessing:      # Serial processing for debugging                                                       

    for args in model_args:                                       
        model = run_model(*args, **kwargs)                  
    

    #============ SAVE RESULTS AT THE RECORDER =============
    import pandas as pd                     
    rec_list = []
    for recorder in model.recorders:
        try:                          
            rec_list.append(str(recorder.node.name))
        except: continue
    timesteps = pd.DataFrame(model.timestepper.datetime_index, columns =['Date'])
    all_recorders_data = timesteps.copy() 

    for rec in model.recorders:
        
        try:
           res = rec.data           
           res_df = pd.DataFrame(res, columns=[ rec.node.name ]) 
           all_recorders_data = pd.concat([all_recorders_data, res_df], axis=1)
        except Exception as e:
           continue 
        
    all_recorders_data.to_csv("/content/cen_sierra_pywr_new/results/all_recorders_output1.csv", index=False)


else:
    import multiprocessing as mp

    num_cores = args.num_cores or mp.cpu_count() - 1

    run_partial = partial(run_model, **kwargs)

    if multiprocessing == 'joblib':
        from joblib import Parallel, delayed

        n_jobs = min(num_cores, len(climate_scenarios))
        output = Parallel(n_jobs=n_jobs)(delayed(run_partial)(*args) for args in model_args)

    else:
        pool = mp.Pool(processes=num_cores)
        for args in model_args:
            pool.apply_async(run_partial, *args)

        pool.close()
        pool.join()

logger.info('Done!')
