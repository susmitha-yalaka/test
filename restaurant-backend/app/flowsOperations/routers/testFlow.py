# testFlow.py
from typing import Dict, Any, List
from app.core.encryptDecrypt import DecryptedRequestData
from app.services import testService
from app.schema.testSchema import AddToCartRequest


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
        return {"version": "3.0", "data": {"status": "active"}}

    screen = decryptedData.screen
    payload = decryptedData.data or {}
    trigger = payload.get("trigger")
    selected_table = payload.get("selectedTable") or payload.get("table") or "table_1"

    if screen == "ADD_ITEMS":
        if not trigger:
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
                }
            }

        if trigger == "filter_menu_items":
            search_q = payload.get("search_query", "")
            menu = await testService.fetch_menu(search_q)
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
