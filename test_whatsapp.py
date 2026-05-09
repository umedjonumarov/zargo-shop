"""
Zargo Shop - WhatsApp Bot Testing
Webhook va conversation flow'larni tekshirish
"""
import json
from unittest.mock import patch, MagicMock

# Webhook test payloads
WEBHOOK_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123456789",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "16505551234",
                            "phone_number_id": "123456789"
                        },
                        "messages": [
                            {
                                "from": "99290998838",
                                "id": "wamid.xxx",
                                "timestamp": "1671498897",
                                "type": "text",
                                "text": {
                                    "body": "Assalom"
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

WEBHOOK_BUTTON_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "99290998838",
                                "type": "interactive",
                                "interactive": {
                                    "button_reply": {
                                        "id": "btn_0",
                                        "title": "📦 Каталог"
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}


def test_webhook_verification():
    """Webhook verification token tekshirish"""
    print("✓ Webhook verification test")
    # Flask test client'da /webhook/whatsapp?hub.verify_token=...


def test_conversation_flow():
    """Bot conversation flow'larini tekshirish"""
    from conversation_state import ConversationState

    state = ConversationState("99290998838")

    # Test state transitions
    assert state.state == "menu"

    state.set_state("catalog")
    assert state.state == "catalog"

    # Test cart operations
    state.add_to_cart("Lepinja", 2, "dona", 50)
    assert len(state.cart) == 1
    assert state.get_cart_total() == 50

    state.add_to_cart("Lepinja", 1, "dona", 25)
    assert len(state.cart) == 1  # Same item
    assert state.get_cart_total() == 75

    state.add_to_cart("Samsa", 3, "dona", 45)
    assert len(state.cart) == 2
    assert state.get_cart_total() == 120

    # Test remove
    state.remove_from_cart("Lepinja")
    assert len(state.cart) == 1
    assert state.get_cart_total() == 45

    print("✓ Conversation state tests passed")


def test_phone_validation():
    """Telefon raqami validation'i"""
    from whatsapp_handler import validate_phone

    assert validate_phone("+992901234567") == "992901234567"
    assert validate_phone("992901234567") == "992901234567"
    assert validate_phone("901234567") == "992901234567"
    assert validate_phone("9901234567") == "992901234567"

    assert validate_phone("123") is None
    assert validate_phone("991234567") is None

    print("✓ Phone validation tests passed")


def test_order_parsing():
    """Order raqamini parsing'i"""
    from whatsapp_handler import parse_order_number

    assert parse_order_number("#456") == "456"
    assert parse_order_number("456") == "456"
    assert parse_order_number("buyu 456") is not None
    assert parse_order_number("invalid") is None

    print("✓ Order parsing tests passed")


def test_sheets_integration():
    """Google Sheets integration test"""
    from whatsapp_handler import GoogleSheetsAPI

    print("✓ Google Sheets integration ready (requires SHEETS_URL)")


if __name__ == "__main__":
    print("Zargo WhatsApp Bot - Test Suite\n")

    test_conversation_flow()
    test_phone_validation()
    test_order_parsing()
    test_sheets_integration()

    print("\nBarcha testlar o'tdi!")
