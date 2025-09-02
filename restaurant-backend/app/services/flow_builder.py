from app.schema.wa_flow import (
    FlowMessage,
    Interactive,
    InteractiveBody,
    InteractiveAction,
    InteractiveActionFlowParameters,
    InteractiveActionParametersFlowActionPayload,
    InteractiveHeader,
    FlowAction,
)


def build_flow_message(
    *,
    to_number: str,
    flow_id: str,
    flow_token: str,
    start_screen: str,
    cta_text: str = "Open",
    header_text: str = "Biz Eats",
    body_text: str = "Start your order below.",
    prefill_data: dict | None = None,
) -> FlowMessage:
    return FlowMessage(
        to=to_number,
        interactive=Interactive(
            header=InteractiveHeader(text=header_text),
            body=InteractiveBody(text=body_text),
            action=InteractiveAction(
                parameters=InteractiveActionFlowParameters(
                    flow_message_version="3.0",
                    flow_token=flow_token,
                    flow_id=flow_id,
                    flow_cta=cta_text,
                    flow_name="Biz Eats Ordering Flow",
                    flow_action=FlowAction.NAVIGATE,
                    flow_action_payload=InteractiveActionParametersFlowActionPayload(
                        screen=start_screen,
                        data=prefill_data or {},
                    ),
                )
            ),
        ),
    )
