# app/routers/testFlow.py
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
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
    """
    Builds a readable cart summary text and computes total.
    Assumes each item has: title(str), price(float), quantity(int)
    """
    lines: List[str] = []
    total_val: float = 0.0
    for item in cart:
        price = float(item.get("price", 0.0))
        qty = int(item.get("quantity", 0))
        line_total = int(price * qty)
        lines.append(f"{item.get('title')} x {qty} – ₹{line_total}")
        total_val += line_total
    return {"cart_review_text": "\n".join(lines), "total": str(int(total_val))}


def _base_data(selected_table: str) -> Dict[str, Any]:
    """
    Always include all required keys so client validators don't fail.
    """
    return {
        "selectedTable": selected_table,
        "menu_items_filtered": [],  # list
        "cart": [],                 # list
        "cart_review_text": "",     # string
        "total": "0",               # string (keep type consistent across screens)
    }


async def processingDecryptedData_restaurant(dd: DecryptedRequestData) -> Dict[str, Any]:
    """
    Core business logic for handling decrypted restaurant flow requests.
    Returns a plain dict; encryption is applied in the route handler.
    """
    if dd.action == "ping":
        return {"version": "3.0", "data": {"status": "active"}}

    screen = dd.screen
    payload = dd.data or {}
    trigger = payload.get("trigger")
    selected_table = payload.get("selectedTable") or payload.get("table") or "table_1"
    # --- new: allow SELECT_TABLE to prefetch data for ADD_ITEMS ---
    if screen == "SELECT_TABLE" and payload.get("trigger") == "init_add_items":
        selected_table = payload.get("selectedTable") or payload.get("table") or "table_1"
        menu = await testService.fetch_menu()
        cart_obj = await testService.fetch_cart(selected_table)
        built = build_cart_review_text(cart_obj["cart"])
        return {
            "version": "3.0",
            "screen": "ADD_ITEMS",   # <-- important: return the NEXT screen and its data
            "data": {
                "selectedTable": selected_table,
                "menu_items_filtered": menu,
                "cart": cart_obj["cart"],
                "cart_review_text": built["cart_review_text"],
                "total": built["total"],
            },
        }

    # -------------------- ADD_ITEMS --------------------
    if screen == "ADD_ITEMS":
        data = _base_data(selected_table)

        # First load of ADD_ITEMS
        if not trigger:
            menu = await testService.fetch_menu()
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            data.update({
                "menu_items_filtered": menu,
                "cart": cart_obj["cart"],
                "cart_review_text": built["cart_review_text"],
                "total": built["total"],
            })
            print("data{data}")
            return {"version": "3.0", "screen": "ADD_ITEMS", "data": data}

        # Filtering menu items
        if trigger == "filter_menu_items":
            search_q = payload.get("search_query", "") or ""
            menu = await testService.fetch_menu(search_q)
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            data.update({
                "menu_items_filtered": menu,
                "cart": cart_obj["cart"],
                "cart_review_text": built["cart_review_text"],
                "total": built["total"],
            })
            return {"version": "3.0", "screen": "ADD_ITEMS", "data": data}

        # Add item to cart
        if trigger == "add_item_to_cart":
            menu_item_id = payload.get("menu_item_id")
            qty = int(payload.get("quantity", 1))
            if not menu_item_id:
                data.update({"error": "No item selected"})
                return {"version": "3.0", "screen": "ADD_ITEMS", "data": data}

            await testService.add_item_to_cart(
                selected_table,
                AddToCartRequest(menu_item_id=int(menu_item_id), quantity=qty),
            )

            # Refresh state after add
            menu = await testService.fetch_menu()
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            data.update({
                "menu_items_filtered": menu,
                "cart": cart_obj["cart"],
                "cart_review_text": built["cart_review_text"],
                "total": built["total"],
                "message": "Item added to cart",
            })
            return {"version": "3.0", "screen": "ADD_ITEMS", "data": data}

    # -------------------- REVIEW_ORDER --------------------
    if screen == "REVIEW_ORDER":
        data = _base_data(selected_table)

        if not trigger:
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj["cart"])
            data.update({
                "cart": cart_obj["cart"],
                "cart_review_text": built["cart_review_text"],
                "total": built["total"],
            })
            return {"version": "3.0", "screen": "REVIEW_ORDER", "data": data}

        if trigger == "confirm_order":
            conf = await testService.confirm_order(selected_table)
            msg = conf.get(
                "confirmation_message",
                "Your order has been placed successfully!",
            )
            return {
                "version": "3.0",
                "screen": "ORDER_CONFIRMED",
                "data": {"confirmation_message": msg},
            }

    # -------------------- Fallback --------------------
    return {"version": "3.0", "screen": screen, "data": _base_data(selected_table)}


@router.post("/restaurantFlow")
async def restaurant_flow_handler(request: RequestData):
    """
    API endpoint for handling restaurant flow requests.
    Decrypts request -> runs business logic -> encrypts response.
    """
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )
        decrypted_data = DecryptedRequestData(**decryptedDataDict)
        print(f"decrypted_data{decrypted_data}")

        # Core logic returns a plain dict (already JSON-safe).
        response_dict = await processingDecryptedData_restaurant(decrypted_data)

        encrypted_response = encryptResponse(response_dict, aes_key, iv)
        return Response(content=encrypted_response, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
