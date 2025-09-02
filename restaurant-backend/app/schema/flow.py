from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class MessagingProduct(str, Enum):
    WHATSAPP = "whatsapp"


class MessageType(str, Enum):
    INTERACTIVE = "interactive"


class RecipientType(str, Enum):
    INDIVIDUAL = "individual"


class InteractiveType(str, Enum):
    FLOW = "flow"


class FlowAction(str, Enum):
    NAVIGATE = "navigate"
    DATA_EXCHANGE = "data_exchange"


class InteractiveBody(BaseModel):
    text: str


class InteractiveActionParametersFlowActionPayload(BaseModel):
    screen: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class InteractiveActionFlowParameters(BaseModel):
    flow_message_version: str = "7.0"
    flow_token: str
    flow_id: str
    flow_cta: str
    flow_name: Optional[str] = None
    flow_action: FlowAction = FlowAction.NAVIGATE
    flow_action_payload: Optional[InteractiveActionParametersFlowActionPayload] = None


class InteractiveAction(BaseModel):
    name: str = "flow"
    parameters: InteractiveActionFlowParameters


class Interactive(BaseModel):
    type: InteractiveType = InteractiveType.FLOW
    body: InteractiveBody
    action: InteractiveAction


class FlowMessage(BaseModel):
    messaging_product: MessagingProduct = MessagingProduct.WHATSAPP
    recipient_type: RecipientType = RecipientType.INDIVIDUAL
    to: str
    type: MessageType = MessageType.INTERACTIVE
    interactive: Interactive
