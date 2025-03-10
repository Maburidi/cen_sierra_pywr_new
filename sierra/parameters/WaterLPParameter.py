import json
import os
import pandas as pd
from calendar import monthrange
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from hashlib import md5

from pywr.parameters import Parameter


class Timestep(object):
    step = None
    datetime = None
    year = None
    month = None


class WaterLPParameter(Parameter):
    store = {}  # TODO: create h5 store on disk (or redis?) to share between class instances

    root_path = os.environ.get('ROOT_S3_PATH')

    # h5store = 'store.h5'

    cfs_to_cms = 1 / 35.315

    mode = 'scheduling'
    res_class = 'network'
    res_name = None
    res_name_full = None
    attr_name = None
    block = None
    month = None
    year = None
    month_offset = None
    month_suffix = ''
    demand_constant_param = ''
    elevation_param = ''

    timestep = Timestep()

    def setup(self):
        super(WaterLPParameter, self).setup()

        self.mode = getattr(self.model, 'mode', self.mode)

        name_parts = self.name.split('/')
        self.res_name = name_parts[0]

        if len(name_parts) >= 2:
            self.attr_name = name_parts[1]

        if self.mode == 'scheduling':
            if len(name_parts) == 3:
                self.block = int(name_parts[2])
        else:
            if len(name_parts) >= 2:
                self.month_offset = int(name_parts[-1]) - 1
            if len(name_parts) == 4:
                self.block = int(name_parts[-2])

        if self.month_offset is not None:
            self.month_suffix = '/{}'.format(self.month_offset + 1)

        try:
            node = self.model.nodes[self.res_name + self.month_suffix]
        except:
            node = None

        if node and 'level' in node.component_attrs or self.attr_name == 'Storage Value':
            self.elevation_param = '{}/Elevation'.format(self.res_name) + self.month_suffix

    def before(self):
        super(WaterLPParameter, self).before()
        self.datetime = self.model.timestepper.current.datetime
        if self.model.mode == 'planning':
            if self.month_offset:
                self.datetime += relativedelta(months=+self.month_offset)

            self.year = self.datetime.year
            self.month = self.datetime.month

        if 4 <= self.datetime.month <= 12:
            self.operational_water_year = self.datetime.year
        else:
            self.operational_water_year = self.datetime.year - 1

    def GET(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, param, timestep=None, scenario_index=None):
        return self.model.parameters[param].value(timestep or self.model.timestep, scenario_index)

    def days_in_month(self, year=None, month=None):
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        return monthrange(year, month)[1]

    def dates_in_month(self, year=None, month=None):
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        start = pd.datetime(year, month, 1)
        ndays = monthrange(year, month)[1]
        dates = pd.date_range(start, periods=ndays).tolist()
        return dates

    def read_csv(self, *args, **kwargs):

        # hashval = md5((str(args) + str(kwargs)).encode()).hexdigest()
        hashval = str(hash(str(args) + str(kwargs)))

        data = self.store.get(hashval)

        if data is None:

            if not args:
                raise Exception("No arguments passed to read_csv.")

            # update args with additional path information

            args = list(args)
            file_path = args[0]

            if '://' in file_path:
                pass
            elif self.root_path:
                if '://' in self.root_path:
                    args[0] = os.path.join(self.root_path, file_path)
                else:
                    args[0] = os.path.join(self.root_path, self.model.metadata['title'], file_path)

            # modify kwargs with sensible defaults
            # TODO: modify these depending on data type (timeseries, array, etc.)

            kwargs['parse_dates'] = kwargs.get('parse_dates', True)
            kwargs['index_col'] = kwargs.get('index_col', 0)
            kwargs['comment'] = kwargs.get('comment', '#')

            # Import data from local files
            # data = pd.read_csv("s3_imports/" + args[0].split('/').pop(), **kwargs)

            # Import data
            # print(args)
            try:
                data = pd.read_csv(*args, **kwargs)
            except:
                print(args)
                raise

            # Saving Data from S3 to a local directory
            # data.to_csv("s3_imports/" + args[0].split('/').pop(), header=True)

            self.store[hashval] = data

        return data

    def get_down_ramp_ifr(self, timestep, value, initial_value=None, rate=0.25):
        if timestep.index == 0:
            if initial_value is not None:
                Qp = initial_value
            else:
                Qp = value
        else:
            Qp = self.model.nodes[self.res_name].prev_flow[-1] / 0.0864  # convert to cms
        return max(value, Qp * (1 - rate))

    def get_up_ramp_ifr(self, timestep, scenario_index, initial_value=None, rate=0.25, max_flow=None):

        if self.model.mode == 'scheduling':
            if initial_value is None:
                raise Exception('Initial maximum ramp up rate cannot be None')
            if timestep.index == 0:
                Qp = initial_value  # should be in cms
            else:
                Qp = self.model.nodes[self.res_name].prev_flow[-1] / 0.0864  # convert to cms
            qmax = Qp * (1 + rate)
        else:
            qmax = 1e6

        if max_flow is not None:
            qmax = min(qmax, max_flow)

        return qmax

    def get_ifr_range(self, timestep, scenario_index, **kwargs):

        param_name = self.res_name + '/Min Requirement' + self.month_suffix
        # min_ifr = self.model.parameters[param_name].get_value(scenario_index) / 0.0864  # convert to cms
        min_ifr = self.model.parameters[param_name].value(timestep, scenario_index) / 0.0864  # convert to cms
        max_ifr = self.get_up_ramp_ifr(timestep, scenario_index, **kwargs)

        ifr_range = max(max_ifr - min_ifr, 0.0)

        return ifr_range



