
import os
from datetime import date
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter




def read_csv(path, start, end):
    df = pd.read_csv(path, index_col=0, header=0, parse_dates=True)[start:end]
    return df



    
def get_energy_df(study,output_dir, basin, start, end):
    path = Path(output_dir, study, basin + '/historical/Livneh', 'Hydropower_Energy_MWh.csv')
    df = read_csv(path, start, end)
    df = df.sum(axis=1) / 1000
    return df
    
    
def plot_basin_energy(basin,scen, start, end, figs_path):
    input_dir = '/content/cen_sierra_pywr_new/data/'
    
    output_dir = '/content/cen_sierra_pywr_new/results/'

    # file_suffix = date.today().strftime('%Y-%m-%d')
    # suffix = ' - {}'.format(file_suffix) if file_suffix else ''
    suffix = ''

    # prices
    prices_path = Path(input_dir, 'common/energy_prices/prices_pivoted_select_years.csv')

    s = pd.read_csv(prices_path, index_col=0, header=0, parse_dates=True).mean(axis=1)
    s.index = pd.to_datetime(s.index, errors='coerce')
    s = s.dropna()
    s = s[s.index.year == 2009]
    s_oct_dec = s[s.index.month >= 10].values
    s_jan_sep = s[s.index.month <= 9].values
    idx_oct_dec = [date(d.year - 1, d.month, d.day) for d in s.index if d.month >= 10]
    idx_jan_sep = [date(d.year, d.month, d.day) for d in s.index if d.month <= 9]
    dates = idx_oct_dec + idx_jan_sep

    prices = pd.Series(
        index=dates,
        data=np.concatenate((s_oct_dec, s_jan_sep))
    )

    if basin == "stanislaus":
        pp = 'Stanislaus_River'
    elif basin == "upper_san_joaquin":      
        pp = 'Upper_San_Joaquin_River'      
    elif basin == "tuolumne":               
        pp = 'Tuolumne_River'                  
    else:
        pp = 'Merced_River'
    
    # full natural flow
    
    fnf_path = os.path.join(input_dir, pp, 'hydrology/historical/Livneh/preprocessed/full_natural_flow_daily_mcm.csv')
    fnf = read_csv(fnf_path, start, end)         
    
    # hydropower 
    hp_no_planning = get_energy_df(scen, output_dir, basin, start, end)
    
    #hp_planning = get_energy_df('planning' + suffix, output_dir, basin, start, end)  
    # prices.index = hp_planning.index 
    
    # figure
    fig, axes = plt.subplots(2, 1, gridspec_kw={'height_ratios': [1, 2]}, figsize=(9, 5))     

    # top
    ax0 = axes[0]
    ax0.plot(prices, color='black')
    ax0.set_ylabel('Price ($/MWh)')
    ax0.xaxis.set_major_formatter(DateFormatter('%b'))
    ax0.set_xlim(prices.index[0], prices.index[-1])

    # bottom
    ax1 = axes[1]
    ax1.plot(hp_no_planning, color='orange', label='Energy w/o planning')
    #ax1.plot(hp_planning, color='green', label='Energy w/ planning')
    ax1.set_ylim(0, 60)
    ax1.set_ylabel('Energy (GWh/day)')

    ax2 = ax1.twinx()
    ax2.plot(fnf, color='blue', label='Full natural flow')
    ax2.set_ylim(0, 60)
    ax2.set_ylabel('Flow (million m$^3$/day)')
    ax2.set_xlim(fnf.index[0], fnf.index[-1])

    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(DateFormatter('%b'))

    fig.tight_layout()
    fig.legend(loc='lower center', ncol=3, frameon=False, borderaxespad=.2)
    plt.subplots_adjust(bottom=0.12)

    

    
    fig.savefig( figs_path + '/usj energy.png' , dpi=600)

    plt.show()
