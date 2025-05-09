import asyncio
import discord
from utils.command_utils import extract_command_argument
from utils.command_utils import CommandValidator
import os
import aiohttp
from aiohttp import web
import threading

class MockMessage:
    def __init__(self, content, attachments=None, reference=None):
        self.content = content
        self.attachments = attachments or []
        self.reference = reference
        self.author = type('Author', (), {'name': 'TestUser'})()
        self.channel = type('Channel', (), {'send': lambda x: print(f"Bot: {x}")})()

class MockAttachment:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content
        self.url = "http://localhost:8080/test_file"

class MockContext:
    def __init__(self, message, command_name="draft"):
        self.message = message
        self.command = type('Command', (), {'name': command_name})()
        self.prefix = "!"
        self.channel = message.channel
        self.author = message.author
        
    async def send(self, content):
        print(f"Bot: {content}")

class Content:
    def __init__(self, content):
        self._content = content
        self._from_file = True
    
    def __str__(self):
        return self._content

async def start_mock_server(content):
    async def handle(request):
        return web.Response(text=content)
    
    app = web.Application()
    app.router.add_get('/test_file', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    return runner

async def test_draft_with_file():
    # Contenuto di test
    test_content = "Questo è un test del contenuto del file.\nContiene più righe.\nE anche caratteri speciali: è, é, ù"
    
    try:
        # Avvia un server mock per simulare l'URL dell'allegato
        runner = await start_mock_server(test_content)
        
        # Crea un mock del messaggio con allegato
        message = MockMessage(
            content="!draft",
            attachments=[MockAttachment("test.txt", test_content)]
        )
        
        # Crea il contesto
        ctx = MockContext(message)
        
        # Testa l'estrazione dell'argomento
        print("\nTest estrazione argomento da file .txt:")
        print("-" * 50)
        success, argument = await extract_command_argument(ctx)
        
        if success:
            print("✅ Test passato!")
            print("Contenuto estratto:")
            print("-" * 20)
            # Verifica se l'argomento è una stringa o un oggetto con _content
            content = getattr(argument, '_content', str(argument))
            print(f"Contenuto:\n{content}")
            print("-" * 20)
        else:
            print("❌ Test fallito!")
            print(f"Errore: {argument}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {str(e)}")
    finally:
        # Ferma il server mock
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(test_draft_with_file()) 