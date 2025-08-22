from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
from app.utils.serialization import encode_payload
from app.services import testService
from app.schema.testSchema import AddToCartRequest
from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,
    encryptResponse,
)

router = APIRouter()


def build_cart_review_text(cart: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Builds a readable cart summary text and computes total."""
    lines, total = [], 0
    for item in cart:
        price = float(item.get("price", 0))
        qty = int(item.get("quantity", 0))
        line_total = int(price * qty)
        lines.append(f"{item.get('title')} x {qty} – ₹{line_total}")
        total += line_total
    return {"cart_review_text": "\n".join(lines), "total": str(total)}


async def processingDecryptedData_restaurant(dd: DecryptedRequestData):
    """Core business logic for handling decrypted restaurant flow requests."""

    if dd.action == "ping":
        return encode_payload({"version": "3.0", "data": {"status": "active"}})

    screen = dd.screen
    payload = dd.data or {}
    trigger = payload.get("trigger")
    selected_table = (
        payload.get("selectedTable") or payload.get("table") or "table_1"
    )

    # -------------------- ADD_ITEMS --------------------
    if screen == "ADD_ITEMS":
        if not trigger:
            menu = await testService.fetch_menu()
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            return encode_payload(
                {
                    "version": "3.0",
                    "screen": "ADD_ITEMS",
                    "data": {
                        "selectedTable": selected_table,
                        "menu_items_filtered": menu,
                        "cart": cart_obj["cart"],
                        "cart_review_text": built["cart_review_text"],
                        "total": built["total"],
                    },
                }
            )

        if trigger == "filter_menu_items":
            search_q = payload.get("search_query", "") or ""
            menu = await testService.fetch_menu(search_q)
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            return encode_payload(
                {
                    "version": "3.0",
                    "screen": "ADD_ITEMS",
                    "data": {
                        "selectedTable": selected_table,
                        "menu_items_filtered": menu,
                        "cart": cart_obj["cart"],
                        "cart_review_text": built["cart_review_text"],
                        "total": built["total"],
                    },
                }
            )

        if trigger == "add_item_to_cart":
            menu_item_id = payload.get("menu_item_id")
            qty = int(payload.get("quantity", 1))
            if not menu_item_id:
                return encode_payload(
                    {
                        "version": "3.0",
                        "screen": "ADD_ITEMS",
                        "data": {"error": "No item selected"},
                    }
                )
            await testService.add_item_to_cart(
                selected_table,
                AddToCartRequest(menu_item_id=int(menu_item_id), quantity=qty),
            )
            # refresh cart after adding
            menu = await testService.fetch_menu()
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            return encode_payload(
                {
                    "version": "3.0",
                    "screen": "ADD_ITEMS",
                    "data": {
                        "selectedTable": selected_table,
                        "menu_items_filtered": menu,
                        "cart": cart_obj["cart"],
                        "cart_review_text": built["cart_review_text"],
                        "total": built["total"],
                        "message": "Item added to cart",
                    },
                }
            )

    # -------------------- REVIEW_ORDER --------------------
    if screen == "REVIEW_ORDER":
        if not trigger:
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            return encode_payload(
                {
                    "version": "3.0",
                    "screen": "REVIEW_ORDER",
                    "data": {
                        "selectedTable": selected_table,
                        "cart_review_text": built["cart_review_text"],
                        "total": built["total"],
                    },
                }
            )

        if trigger == "confirm_order":
            conf = await testService.confirm_order(selected_table)
            msg = conf.get(
                "confirmation_message",
                "Your order has been placed successfully!",
            )
            return encode_payload(
                {
                    "version": "3.0",
                    "screen": "ORDER_CONFIRMED",
                    "data": {"confirmation_message": msg},
                }
            )

    # -------------------- fallback --------------------
    return encode_payload({"version": "3.0", "screen": screen, "data": {}})


@router.post("/restaurantFlow")
async def restaurant_flow_handler(request: RequestData):
    """API endpoint for handling restaurant flow requests."""
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )

        decrypted_data = DecryptedRequestData(**decryptedDataDict)

        response_data = await processingDecryptedData_restaurant(decrypted_data)

        encrypted_response = encryptResponse(response_data, aes_key, iv)

        return Response(
            content=encrypted_response, media_type="application/octet-stream"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
