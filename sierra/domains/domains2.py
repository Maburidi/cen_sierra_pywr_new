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


class Hydropower(PiecewiseLink):
    """
    A hydropower plant node compatible with the new Pywr version.
    """

    __parameter_attributes__ = ("costs", "max_flows", "flow_capacity", "turbine_capacity")  # Let Pywr handle these

    def __init__(self, model, turbine_capacity=None, flow_capacity=None, residual_flow=0.0, residual_cost=0.0, **kwargs):
        """Initialize a new Hydropower instance."""

        self.head = kwargs.pop('head', None)  # Fixed head
        self.efficiency = kwargs.pop('efficiency', 0.9)  # Turbine efficiency
        self.tailwater_elevation = kwargs.pop('tailwater_elevation', 0.0)

        self.water_elevation_reservoir = kwargs.pop('water_elevation_reservoir', None)
        self.water_elevation_parameter = kwargs.pop('water_elevation_parameter', None)

        self.turbine_capacity = turbine_capacity
        self.residual_flow = residual_flow
        self.residual_cost = residual_cost

        # Call the superclass constructor (PiecewiseLink1)
        super().__init__(model, **kwargs)

        # Force Pywr to resolve parameter references
        #timestep = model.timestepper.start  
        #scenario_index = 0    

        #self.costs = [c.value(timestep, scenario_index) if hasattr(c, 'value') else c for c in self.costs]

        #print(f"Initialized Costs in {self.name}: {self.costs}")

        # Ensure output max_flow is set correctly
        self.output.max_flow = flow_capacity

    def after(self, timestep):
        """Set total flow on this link as sum of sublinks after each timestep."""
        for lnk in self.sublinks:
            self.commit_all(lnk.flow)
        super(Hydropower, self).after(timestep)








class InstreamFlowRequirement(Node):

    __parameter_attributes__ = ("costs", "max_flows")


    def __init__(self, model,nsteps, *args, **kwargs):
        self.allow_isolated = True
        name = kwargs.pop("name")
                
        #costs = kwargs.pop("costs", None)
        costs = kwargs.pop('costs', None)
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
            if len(self.sublinks) != len(values):
                raise ValueError(
                    f"Piecewise costs must be the same length as the number of "
                    f"sub-links ({len(self.sublinks)})."
                )
            for i, sl in enumerate(self.sublinks):
                sl.cost = values[i]

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
                sl.max_flow = values[i]

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







