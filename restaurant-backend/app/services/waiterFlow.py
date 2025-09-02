from app.schema.flow import (
    FlowMessage,
    Interactive,
    InteractiveBody,
    InteractiveAction,
    InteractiveActionFlowParameters,
    InteractiveActionParametersFlowActionPayload,
)


def waiter_flow(to_number: str) -> FlowMessage:
    """
    Build the interactive flow message for Biz Eats
    """
    return FlowMessage(
        to=to_number,
        interactive=Interactive(
            body=InteractiveBody(
                text="Proceed with your order by selecting a table and adding menu items."
            ),
            action=InteractiveAction(
                parameters=InteractiveActionFlowParameters(
                    flow_token="biz_eats_start",
                    flow_id="TEST_FLOW_BIZ_EATS_7.0.1",
                    flow_cta="Start Order",
                    flow_name="Biz Eats Ordering Flow",
                    flow_action_payload=InteractiveActionParametersFlowActionPayload(
                        screen="SELECT_TABLE"
                    ),
                )
            ),
        ),
    )
