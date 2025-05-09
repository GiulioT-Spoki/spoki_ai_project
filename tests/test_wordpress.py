import asyncio
from utils.wordpress_handler import WordPressHandler

async def main():
    wp_handler = WordPressHandler()
    success, message = await wp_handler.test_connection()
    print(message)

if __name__ == "__main__":
    asyncio.run(main())