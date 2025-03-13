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








from pywr.nodes import Node
from pywr.parameters import load_parameter

class InstreamFlowRequirement(PiecewiseLink):
    """
    An instream flow requirement node compatible with the new Pywr version.
    """

    __parameter_attributes__ = ("costs", "max_flows")  # Let Pywr handle these automatically

    def __init__(self, model, ifr_type="basic", **kwargs):
        """Initialize a new InstreamFlowRequirement instance."""

        # Assign IFR type
        self.ifr_type = ifr_type

        # Extract and set additional parameters
        self.min_flow = kwargs.pop("min_flow", 0.0)
        self.min_flow_cost = kwargs.pop("min_flow_cost", 0.0)
        self.max_flow_cost = kwargs.pop("max_flow_cost", 0.0)

        # Call the superclass constructor (PiecewiseLink1)
        super().__init__(model, **kwargs)

        # 🔹 Force Pywr to resolve parameter references
        #timestep = model.timestepper.start  # Get the first timestep
        #scenario_index = 0  # Default scenario

        #self.costs = [c.value(timestep, scenario_index) if hasattr(c, "value") else c for c in self.costs]

        #print(f"🚀 Initialized Costs in {self.name}: {self.costs}")

    def after(self, timestep):
        """Set total flow on this link as sum of sublinks after each timestep."""
        for lnk in self.sublinks:
            self.commit_all(lnk.flow)
        super(InstreamFlowRequirement, self).after(timestep)







