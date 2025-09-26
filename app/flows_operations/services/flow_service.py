from requests import Session
from app.core import config
from app.flows_operations.schema import (
    FlowMessage,
    Interactive,
    InteractiveAction,
    InteractiveActionFlowParameters,
    InteractiveActionParametersFlowActionPayload,
    InteractiveBody,
)
from app.routers import products as products_router
from app.routers import orders as orders_router


def seller_flow(to_number: str, db: Session) -> FlowMessage:
    """
    Build the interactive flow message
    """
    categories = products_router.categories(db)
    variants = products_router.all_variants(db)
    orders = orders_router.list_orders(db)
    print(f"categories{categories} variants{variants} orders{orders}")
    return FlowMessage(
        to=to_number,
        interactive=Interactive(
            body=InteractiveBody(text="Proceed with managing the orders and inventory."),
            action=InteractiveAction(
                parameters=InteractiveActionFlowParameters(
                    flow_message_version="3",
                    flow_token="biz_boutique",
                    flow_cta="Start",
                    flow_id=config.FLOW_ID,
                    flow_action_payload=InteractiveActionParametersFlowActionPayload(
                        screen="CHOOSE_NAV",
                        data={
                            "categories": categories,
                            "items": variants,
                            "orders": orders
                        }
                        ),
                )
            ),
        ),
    )
