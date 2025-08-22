# app/routers/testFlow.py

from decimal import Decimal
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.core.encryptDecrypt import (
    DecryptedRequestData,
    RequestData,
    decryptRequest,      # function to decrypt incoming data (returns decryptedData, aes_key, iv)
    encryptResponse      # function to encrypt outgoing response
)
from app.services import testService
from app.schema.testSchema import AddToCartRequest


router = APIRouter()
log = logging.getLogger("flow.routers")


def build_cart_review_text(cart: List[Dict[str, Any]]) -> Dict[str, Any]:
    lines = []
    total_val = 0
    for item in cart:
        price = float(item.get("price", 0))
        qty = int(item.get("quantity", 0))
        line_total = int(price * qty)
        lines.append(f"{item.get('title')} x {qty} – ₹{line_total}")
        total_val += line_total
    return {"cart_review_text": "\n".join(lines), "total": str(total_val)}


async def processingDecryptedData_restaurant(decryptedData: DecryptedRequestData):
    if decryptedData.action == "ping":
        print(f"decryptedData{decryptedData}")
        return {"version": "3.0", "data": {"status": "active"}}

    screen = decryptedData.screen
    payload = decryptedData.data or {}
    trigger = payload.get("trigger")
    selected_table = payload.get("selectedTable") or payload.get("table") or "table_1"

    if screen == "ADD_ITEMS":
        if not trigger:
            menu = await testService.fetch_menu()
            print(f"menu{menu}")
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj.get("cart", []))
            return {
                "version": "3.0",
                "screen": "ADD_ITEMS",
                "data": {
                    "selectedTable": selected_table,
                    "menu_items_filtered": menu,
                    "cart": cart_obj.get("cart", []),
                    "cart_review_text": built["cart_review_text"],
                    "total": built["total"],
                }
            }

        if trigger == "filter_menu_items":
            search_q = payload.get("search_query", "")
            menu = await testService.fetch_menu(search_q)
            menu_encoded = jsonable_encoder(menu)
            print(f"menu{menu_encoded}")
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj.get("cart", []))
            print(f"cart{cart_obj}, built{built}")
            print(f"selectedTable, {selected_table},menu_items_filtered: {menu_encoded},cart: {cart_obj.get("cart", [])},")
            print(f"cart_review_text: {built["cart_review_text"]},total: {built["total"]}")
            payload = {
                "version": "3.0",
                "screen": "ADD_ITEMS",
                "data": {
                    "selectedTable": selected_table,
                    "menu_items_filtered": menu_encoded,
                    "cart": cart_obj.get("cart", []),
                    "cart_review_text": built["cart_review_text"],
                    "total": built["total"],
                }
            }
            encoded = jsonable_encoder(payload,  custom_encoder={Decimal: float})
            return JSONResponse(Content=encoded)

        if trigger == "add_item_to_cart":
            selected_item = payload.get("selectedItem")
            qty = int(payload.get("quantity", 1))
            if not selected_item:
                return {"version": "3.0", "screen": "ADD_ITEMS", "data": {"error": "No item selected"}}
            add_payload = AddToCartRequest(selectedItem=selected_item, quantity=qty)
            await testService.add_item_to_cart(selected_table, add_payload)
            menu = await testService.fetch_menu()
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj.get("cart", []))
            return {
                "version": "3.0",
                "screen": "ADD_ITEMS",
                "data": {
                    "selectedTable": selected_table,
                    "menu_items_filtered": menu,
                    "cart": cart_obj.get("cart", []),
                    "cart_review_text": built["cart_review_text"],
                    "total": built["total"],
                    "message": "Item added to cart",
                }
            }

    if screen == "REVIEW_ORDER":
        if not trigger:
            cart_obj = await testService.fetch_cart(selected_table)
            built = build_cart_review_text(cart_obj.get("cart", []))
            return {
                "version": "3.0",
                "screen": "REVIEW_ORDER",
                "data": {
                    "selectedTable": selected_table,
                    "cart": cart_obj.get("cart", []),
                    "cart_review_text": built["cart_review_text"],
                    "total": built["total"],
                }
            }

        if trigger == "confirm_order":
            confirmation = await testService.confirm_order(selected_table)
            confirmation_message = confirmation.get("confirmation_message", "Your order has been placed successfully!")
            return {"version": "3.0", "screen": "ORDER_CONFIRMED", "data": {"confirmation_message": confirmation_message}}

    return {"version": "3.0", "screen": screen, "data": {}}


@router.post("/restaurantFlow")
async def restaurant_flow_handler(request: RequestData):
    print(f"request{request}")
    try:
        decryptedDataDict, aes_key, iv = decryptRequest(
            request.encrypted_flow_data,
            request.encrypted_aes_key,
            request.initial_vector,
        )

        decrypted_data = DecryptedRequestData(**decryptedDataDict)

        response_data = await processingDecryptedData_restaurant(decrypted_data)
        print(f"response_data{response_data}")

        encrypted_response = encryptResponse(response_data, aes_key, iv)

        return Response(content=encrypted_response, media_type="application/octet-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
