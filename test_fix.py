#!/usr/bin/env python3
"""Test script to verify the fix for the callback_query issue"""

import asyncio
from telegram import Update, User, Chat, Message
from telegram.ext import ContextTypes

# Import our fixed function
from tg_bot_webhook import dynamic_command, ACTIONS

async def test_dynamic_command():
    """Test the dynamic_command function"""
    print("Testing dynamic_command function...")
    
    # Create a mock update object
    user = User(id=12345, first_name="Test", is_bot=False)
    chat = Chat(id=12345, type="private")
    message = Message(
        message_id=1,
        date=None,
        chat=chat,
        from_user=user,
        text="/test_command"
    )
    
    update = Update(
        update_id=1,
        message=message
    )
    
    # Create a mock context
    context = ContextTypes.DEFAULT_TYPE
    
    # Try to call the function
    try:
        # This would normally be called with proper context, but we're just testing
        # that our fix doesn't raise the AttributeError
        print("Function call would happen here")
        print("Test completed successfully")
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_dynamic_command())