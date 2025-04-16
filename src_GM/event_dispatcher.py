# src_GM/event_dispatcher.py
from abc import ABC, abstractmethod
from typing import List, Dict

from world import Event  # Import the Event namedtuple
from agent.agent import Agent  # Import the Agent class


class BaseEventDispatcher(ABC):
    """
    Abstract Base Class for strategies that determine which agents
    should perceive an event and deliver it to them.
    """

    @abstractmethod
    def dispatch_event(self, event: Event, registered_agents: Dict[str, Agent], agent_locations: Dict[str, str]) -> List[str]:
        """
        Determines which agents perceive the event and calls their perceive method.

        Args:
            event: The Event object to dispatch.
            registered_agents: A dictionary mapping agent names to Agent objects.
            agent_locations: A dictionary mapping agent names to their current location strings.

        Returns:
            A list of agent names to whom the event was successfully dispatched.
        """
        pass


class DirectEventDispatcher(BaseEventDispatcher):
    """
    Dispatches events based on scope and agent location.
    - Global events go to everyone.
    - Local events go to agents at that location.
    - Action outcomes go to agents at that location.
    (Based on the logic previously in WorldState.log_event)
    """

    def dispatch_event(self, event: Event, registered_agents: Dict[str, Agent], agent_locations: Dict[str, str]) -> List[str]:
        dispatched_to = []
        # Log processing start
        print(
            f"[Dispatcher '{type(self).__name__}']: Processing event: {event.scope} @ {event.location or 'Global'} - '{event.description[:50]}...'")

        for agent_name, agent_obj in registered_agents.items():
            agent_current_loc = agent_locations.get(agent_name)
            should_perceive = False

            # Determine if the agent should perceive based on scope and location
            if event.scope == 'global':
                should_perceive = True
            elif event.location == agent_current_loc:  # Check if agent is at the event location
                if event.scope == 'local':
                    should_perceive = True
                elif event.scope == 'action_outcome':
                    # Original logic: Dispatch action outcome even to the agent who performed it.
                    # The agent's memory/processing can decide how to handle it (e.g., ignore if redundant).
                    # If filtering is desired *here*, uncomment the check below:
                    # if event.triggered_by != agent_name:
                    #    should_perceive = True
                    should_perceive = True  # Current: Dispatch action outcome to all at location

            # If perception criteria met, attempt to call agent's perceive method
            if should_perceive:
                try:
                    # print(f"[Dispatcher]: Attempting to dispatch to {agent_name}...") # Debug
                    # Call the agent's perception handler
                    agent_obj.perceive(event)
                    dispatched_to.append(agent_name)
                except AttributeError:
                    print(
                        f"[Dispatcher Error]: Agent {agent_name} object lacks 'perceive' method!")
                except Exception as e:
                    print(
                        f"[Dispatcher Error]: Failed during perceive call for {agent_name}: {e}")

        if dispatched_to:
            print(
                f"[Dispatcher '{type(self).__name__}']: Event dispatched to: {dispatched_to}")
        # else:
            # print(f"[Dispatcher '{type(self).__name__}']: Event not dispatched to any agents based on rules.") # Can be verbose

        return dispatched_to
