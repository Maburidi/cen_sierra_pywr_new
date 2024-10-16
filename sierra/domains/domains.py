from pywr.nodes import Domain, PiecewiseLink, Storage, Output, Input, Node
from loguru import logger

from pywr.parameters import (
    pop_kwarg_parameter,
    load_parameter,
    load_parameter_values,
    FlowDelayParameter,
)




class Reservoir(Storage):
    """
    Like a storage node, only better
    """

    def __init__(self, *args, **kwargs):
        self.gauge = kwargs.pop("gauge", None)
        super(Reservoir, self).__init__(*args, **kwargs)

'''
class Hydropower(PiecewiseLink):
    """
    A hydropower plant.
    """

    _type = 'hydropower'

    def __init__(self, model, turbine_capacity=None, flow_capacity=None, residual_flow=0.0, residual_cost=0.0,
                 **kwargs):
        """Initialise a new Hydropower instance
        Parameters
        ----------
        """

        self.head = kwargs.pop('head', None)  # Fixed head
        self.efficiency = kwargs.pop('efficiency', 0.9)  # Turbine efficiency
        self.tailwater_elevation = kwargs.pop('tailwater_elevation', 0.0)

        max_flows = kwargs.pop('max_flow', [])
        costs = kwargs.pop('cost', [])
        max_flows_ = kwargs.pop('max_flow', None)
        costs_ = kwargs.pop('cost', None)
             

        # Add an unconstrained block with a default cost of zero
        if len(max_flows) < len(costs):
            max_flows.append(None)
        if len(costs) < len(max_flows):
            costs.append(0.0)  # PiecewiseLink will raise an error if not same length

        kwargs['max_flows'] = max_flows
        kwargs['costs'] = costs
        kwargs['nsteps'] = len(costs)


        self.water_elevation_reservoir = kwargs.pop('water_elevation_reservoir', None)
        self.water_elevation_parameter = kwargs.pop('water_elevation_parameter', None)
        self.turbine_capacity = turbine_capacity
        self.residual_flow = residual_flow
        self.residual_cost = residual_cost
        print("==============hello=============")
        for key, value in kwargs.items():
            print(f"{key}: {value}")  # Print each key-value pair
        print("================================")

        super(Hydropower, self).__init__(model, **kwargs)

        # do this after super(...).__init__(...)
        self.output.max_flow = flow_capacity

    @classmethod
    def load(cls, data, model):
        max_flow = data.pop('max_flow', data.pop('max_flows', None))
        if type(max_flow) == list:
            max_flows = max_flow
        else:
            max_flows = [max_flow]
        max_flows = [load_parameter(model, x) for x in max_flows]
        cost = data.pop('cost', data.pop('costs', None))
        if type(cost) == list:
            costs = cost
        else:
            costs = [cost]
        costs = [load_parameter(model, c) for c in costs]
        turbine_capacity = load_parameter(model, data.pop('turbine_capacity', None))
        flow_capacity = load_parameter(model, data.pop('flow_capacity', None))
        data['head'] = load_parameter(model, data.pop('head', None))
        data['efficiency'] = load_parameter(model, data.pop('efficiency', 0.9))
        data['tailwater_elevation'] = load_parameter(model, data.pop('tailwater_elevation', 0.0))
        residual_flow = data.pop('residual_flow', 0.0)
        residual_cost = data.pop('residual_cost', 0.0)
        param_type = data.pop('type')
        try:
            node = cls(model, turbine_capacity, flow_capacity, residual_flow, residual_cost, max_flows=max_flows,
                       costs=costs, **data)
        except:
            logger.error('{} {} failed to load'.format(param_type, data['name']))
            raise
        return node
'''


class Hydropower(Node):

    __parameter_attributes__ = ("costs", "max_flows","flow_capacity")


    def __init__(self, model,nsteps,turbine_capacity=None, flow_capacity=None, residual_flow=0.0, residual_cost=0.0, *args, **kwargs):
        self.allow_isolated = True
        name = kwargs.pop("name")
        costs = kwargs.pop("costs", None)
        max_flows = kwargs.pop("max_flows", None)
             

        self.head = kwargs.pop('head', None)  # Fixed head
        self.efficiency = kwargs.pop('efficiency', 0.9)  # Turbine efficiency
        self.tailwater_elevation = kwargs.pop('tailwater_elevation', 0.0)
        self.water_elevation_reservoir = kwargs.pop('water_elevation_reservoir', None)
        self.water_elevation_parameter = kwargs.pop('water_elevation_parameter', None)
        self.turbine_capacity = turbine_capacity
        self.residual_flow = residual_flow
        self.residual_cost = residual_cost    

    
        # TODO look at the application of Domains here. Having to use
        # Input/Output instead of BaseInput/BaseOutput because of a different
        # domain is required on the sub-nodes and they need to be connected
        self.sub_domain = Domain()
        self.input = Input(model, name="{} Input".format(name), parent=self)
        self.output = Output(model, name="{} Output".format(name), parent=self)

        self.sub_output = Output(
            model,
            name="{} Sub Output".format(name),
            parent=self,
            domain=self.sub_domain,
        )
        self.sub_output.connect(self.input)
        self.sublinks = []
        for i in range(nsteps):
            sublink = Input(
                model,
                name="{} Sublink {}".format(name, i),
                parent=self,
                domain=self.sub_domain,
            )
            self.sublinks.append(sublink)
            sublink.connect(self.sub_output)
            self.output.connect(self.sublinks[-1])

        super().__init__(model, *args, name=name, **kwargs)

        if costs is not None:
            self.costs = costs
        if max_flows is not None:
            self.max_flows = max_flows                
        
        self.output.max_flow = flow_capacity

    def get_min_flow(self, si):
        return sum([sl.get_min_flow(si) for sl in self.sublinks])

    def get_max_flow(self, si):
        return sum([sl.get_max_flow(si) for sl in self.sublinks])

    def costs():
        def fget(self):
            return [sl.cost for sl in self.sublinks]

        def fset(self, values):
            print("len(self.sublinks)", len(self.sublinks))
            print("len(values)", len(values))
            if len(self.sublinks) != len(values):
                raise ValueError(
                    f"Piecewise costs must be the same length as the number of "
                    f"sub-links ({len(self.sublinks)})."
                )
            for i, sl in enumerate(self.sublinks):
                print('---------')
                print(values[i])

                sl.cost = values[i]
            print("-----Done Costs----")

        return locals()

    costs = property(**costs())

    def max_flows():
        def fget(self):
            return [sl.max_flow for sl in self.sublinks]

        def fset(self, values):
            if len(self.sublinks) != len(values):
                raise ValueError(
                    f"Piecewise max_flows must be the same length as the number of "
                    f"sub-links ({len(self.sublinks)})."
                )
            for i, sl in enumerate(self.sublinks):
                print('---------')
                print(values[i])

                sl.max_flow = values[i]
            print("-----Done Max_flows----")

        return locals()

    max_flows = property(**max_flows())

    def iter_slots(self, slot_name=None, is_connector=True):
        if is_connector:
            yield self.input
        else:
            yield self.output

    def after(self, timestep):
        """
        Set total flow on this link as sum of sublinks
        """
        for lnk in self.sublinks:
            self.commit_all(lnk.flow)
        # Make sure save is done after setting aggregated flow
        super(Hydropower, self).after(timestep)


    @classmethod
    def load(cls, data, model):
        max_flow = data.pop('max_flow', data.pop('max_flows', None))
        if type(max_flow) == list:
            max_flows = max_flow
        else:
            max_flows = [max_flow]
        max_flows = [load_parameter(model, x) for x in max_flows]
        cost = data.pop('cost', data.pop('costs', None))
        if type(cost) == list:
            costs = cost
        else:
            costs = [cost]
        costs = [load_parameter(model, c) for c in costs]
        turbine_capacity = load_parameter(model, data.pop('turbine_capacity', None))
        flow_capacity = load_parameter(model, data.pop('flow_capacity', None))
        data['head'] = load_parameter(model, data.pop('head', None))
        data['efficiency'] = load_parameter(model, data.pop('efficiency', 0.9))
        data['tailwater_elevation'] = load_parameter(model, data.pop('tailwater_elevation', 0.0))
        residual_flow = data.pop('residual_flow', 0.0)
        residual_cost = data.pop('residual_cost', 0.0)
        param_type = data.pop('type')
        try:
            node = cls(model, turbine_capacity, flow_capacity, residual_flow, residual_cost, max_flows=max_flows,
                       costs=costs, **data)
        except:
            logger.error('{} {} failed to load'.format(param_type, data['name']))
            raise
        return node








class InstreamFlowRequirement(Node):

    __parameter_attributes__ = ("costs", "max_flows")


    def __init__(self, model,nsteps, *args, **kwargs):
        self.allow_isolated = True
        name = kwargs.pop("name")
                
        #costs = kwargs.pop("costs", None)
        costs = kwargs.pop('costs', None)
        print("--------costs--------")
        print(costs)
        max_flows = kwargs.pop('max_flows', None)

        self.min_flows = kwargs.pop("min_flows", None)
        self.min_flow_cost = kwargs.pop('min_flow_cost', None)         
        self.max_flow_cost = kwargs.pop('max_flow_cost', None) 

        self.ifr_type = kwargs.pop('ifr_type', 'basic')
        

        # TODO look at the application of Domains here. Having to use
        # Input/Output instead of BaseInput/BaseOutput because of a different
        # domain is required on the sub-nodes and they need to be connected
        self.sub_domain = Domain()
        self.input = Input(model, name="{} Input".format(name), parent=self)
        self.output = Output(model, name="{} Output".format(name), parent=self)

        self.sub_output = Output(
            model,
            name="{} Sub Output".format(name),
            parent=self,
            domain=self.sub_domain,
        )
        self.sub_output.connect(self.input)
        self.sublinks = []
        for i in range(nsteps):
            sublink = Input(
                model,
                name="{} Sublink {}".format(name, i),
                parent=self,
                domain=self.sub_domain,
            )
            self.sublinks.append(sublink)
            sublink.connect(self.sub_output)
            self.output.connect(self.sublinks[-1])

        super().__init__(model, *args, name=name, **kwargs)

        if costs is not None:
            self.costs = costs
        if max_flows is not None:
            self.max_flows = max_flows


    def get_min_flow(self, si):
        return sum([sl.get_min_flow(si) for sl in self.sublinks])

    def get_max_flow(self, si):
        return sum([sl.get_max_flow(si) for sl in self.sublinks])

    def costs():
        def fget(self):
            return [sl.cost for sl in self.sublinks]

        def fset(self, values):
            print("len(self.sublinks)", len(self.sublinks))
            print("len(values)", len(values))
            if len(self.sublinks) != len(values):
                raise ValueError(
                    f"Piecewise costs must be the same length as the number of "
                    f"sub-links ({len(self.sublinks)})."
                )
            for i, sl in enumerate(self.sublinks):
                print('---------')
                print(values[i])

                sl.cost = values[i]
            print("-----Done Costs----")

        return locals()

    costs = property(**costs())

    def max_flows():
        def fget(self):
            return [sl.max_flow for sl in self.sublinks]

        def fset(self, values):
            if len(self.sublinks) != len(values):
                raise ValueError(
                    f"Piecewise max_flows must be the same length as the number of "
                    f"sub-links ({len(self.sublinks)})."
                )
            for i, sl in enumerate(self.sublinks):
                print('---------')
                print(values[i])

                sl.max_flow = values[i]
            print("-----Done Max_flows----")

        return locals()

    max_flows = property(**max_flows())

    def iter_slots(self, slot_name=None, is_connector=True):
        if is_connector:
            yield self.input
        else:
            yield self.output

    def after(self, timestep):
        """
        Set total flow on this link as sum of sublinks
        """
        for lnk in self.sublinks:
            self.commit_all(lnk.flow)
        # Make sure save is done after setting aggregated flow
        super(InstreamFlowRequirement, self).after(timestep)


    @classmethod
    def load(cls, data, model):
        
        cost = data.pop('costs', data.pop('cost', 0.0))
        
        min_flow = data.pop('min_flow', data.pop('min_flows', None))
        min_flow_cost = data.pop("min_flow_cost", 0.0)
        
        max_flow = data.pop('max_flow', data.pop('max_flows', None))        
        max_flow_cost = data.pop("max_flow_cost", 0.0)

        if type(max_flow) == list:
            max_flow = [load_parameter(model, x) for x in max_flow]
        else:
            max_flow = [load_parameter(model, min_flow), load_parameter(model, max_flow)]

        if type(cost) == list:
            cost = [load_parameter(model, x) for x in cost]
        else:
            cost = [load_parameter(model, min_flow_cost),
                    load_parameter(model, 0.0),
                    load_parameter(model, max_flow_cost)]

        data['max_flows'] = max_flow
        data['costs'] = cost

        del data["type"]
        node = cls(model, **data)
        return node











'''
class InstreamFlowRequirement(PiecewiseLink):
    """An instream flow requirement node
    """
    _type = 'InstreamFlowRequirement'

    def __init__(self, model, **kwargs):
        """Initialise a new InstreamFlowRequirement instance
        Parameters
        to-be-complete




        max_flows = kwargs.pop('max_flows', [])
        costs = kwargs.pop('costs', [])
        max_flows_ = kwargs.pop('max_flow', None)
        costs_ = kwargs.pop('cost', None)
             

        # Add an unconstrained block with a default cost of zero
        if len(max_flows) < len(costs):
            max_flows.append(None)
        if len(costs) < len(max_flows):
            costs.append(0.0)  # PiecewiseLink will raise an error if not same length

        kwargs['max_flows'] = max_flows
        kwargs['costs'] = costs
        kwargs['nsteps'] = len(costs)


        self.water_elevation_reservoir = kwargs.pop('water_elevation_reservoir', None)
        self.water_elevation_parameter = kwargs.pop('water_elevation_parameter', None)
        self.turbine_capacity = turbine_capacity

        """
        # create keyword arguments for PiecewiseLink
        
        #max_flows = kwargs.pop('max_flows', []) 
        max_flows = kwargs.pop('min_flows', [])        
        costs = kwargs.pop('costs', [])                
        min_flows_ = kwargs.pop('min_flow', None)      
        costs_ = kwargs.pop('cost', None)              

        
        self.min_flow_cost = kwargs.pop('min_flow_cost', None)         
        self.max_flow_cost = kwargs.pop('max_flow_cost', None)         

        if len(max_flows) < len(costs):
            max_flows.append(None)
        if len(costs) < len(max_flows):
            costs.append(0.0)          

        #kwargs['max_flows'] = max_flows    
        kwargs['max_flows'] = max_flows    
        kwargs['costs'] = costs
        kwargs['nsteps'] = len(costs) 
        
        #kwargs['max_flow'].append(None)
        #try:
        #    assert (len(kwargs['costs']) == len(kwargs['max_flows']))
        #except:
        #    raise

        self.ifr_type = kwargs.pop('ifr_type', 'basic')
        
        super().__init__(model, **kwargs)
        
    @classmethod
    def load(cls, data, model):
        
        cost = data.pop('costs', data.pop('cost', None))
        
        min_flow = data.pop('max_flows', data.pop('max_flows', None))
        min_flow_cost = data.pop("min_flow_cost", 0.0)
        
        max_flow = data.pop('min_flows', data.pop('min_flow', None))        
        max_flow_cost = data.pop("max_flow_cost", 0.0)

        if type(max_flow) == list:
            max_flow = [load_parameter(model, x) for x in max_flow]
        else:
            max_flow = [load_parameter(model, min_flow), load_parameter(model, max_flow)]

        if type(cost) == list:
            cost = [load_parameter(model, x) for x in cost]
        else:
            cost = [load_parameter(model, min_flow_cost),
                    load_parameter(model, 0.0),
                    load_parameter(model, max_flow_cost)]

        data['max_flow'] = max_flow
        data['cost'] = cost

        del data["type"]
        node = cls(model, **data)
        return node
'''




