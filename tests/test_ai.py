import asyncio
from utils.ai_handler import AIHandler

async def main():
    ai_handler = AIHandler()
    success, message, _ = await ai_handler.generate_article("test")
    print(message)

if __name__ == "__main__":
    asyncio.run(main()) 