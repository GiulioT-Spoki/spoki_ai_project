import asyncio
import discord
from utils.command_utils import extract_command_argument
import json
import os
import aiohttp
from aiohttp import web

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

def load_prompt_template():
    with open('config/prompts.json', 'r') as f:
        prompts = json.load(f)
    return prompts['article_generation']['template']

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
    try:
        # Leggi il contenuto del file di test
        with open('test_article.txt', 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Avvia il server mock
        runner = await start_mock_server(file_content)
        
        try:
            # Crea un mock del messaggio con allegato
            message = MockMessage(
                content="!draft",
                attachments=[MockAttachment("test_article.txt", file_content)]
            )
            
            # Crea il contesto
            ctx = MockContext(message)
            
            # Testa l'estrazione dell'argomento
            print("\nTest estrazione argomento da file .txt:")
            print("-" * 50)
            success, argument = await extract_command_argument(ctx)
            
            if success:
                print("✅ Test passato!")
                print("\nContenuto estratto dal file:")
                print("-" * 20)
                print(str(argument))
                print("-" * 20)
                
                # Carica il template del prompt
                prompt_template = load_prompt_template()
                
                # Simula input utente
                user_input = "parla in rima"  # linea guida aggiuntiva
                
                # Popola il prompt come farebbe il bot
                populated_prompt = prompt_template.format(
                    topic=user_input,
                    content=file_content
                )
                
                print("\nPrompt generato:")
                print("-" * 20)
                print(populated_prompt)
                print("-" * 20)
            else:
                print("❌ Test fallito!")
                print(f"Errore: {argument}")
        finally:
            # Ferma il server mock
            await runner.cleanup()
            
    except Exception as e:
        print(f"❌ Errore durante il test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_draft_with_file()) 