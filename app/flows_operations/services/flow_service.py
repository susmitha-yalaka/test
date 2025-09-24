from app.core import config
from app.flows_operations.schema import (
    FlowMessage,
    Interactive,
    InteractiveAction,
    InteractiveActionFlowParameters,
    InteractiveActionParametersFlowActionPayload,
    InteractiveBody,
)


def waiter_flow(to_number: str) -> FlowMessage:
    """
    Build the interactive flow message
    """
    return FlowMessage(
        to=to_number,
        interactive=Interactive(
            body=InteractiveBody(text="Proceed with placing the order by selecting a table and adding menu items."),
            action=InteractiveAction(
                parameters=InteractiveActionFlowParameters(
                    flow_message_version="3",
                    flow_token="biz_boutique",
                    flow_cta="Start",
                    flow_id=config.FLOW_ID,
                    flow_action_payload=InteractiveActionParametersFlowActionPayload(screen="SELECT_TABLE"),
                )
            ),
        ),
    )
