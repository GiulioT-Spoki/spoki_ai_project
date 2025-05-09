import asyncio
import discord
from utils.command_utils import extract_command_argument
from utils.ai_handler import AIHandler
from utils.wordpress_handler import WordPressHandler
import json
import os
import aiohttp
from aiohttp import web
import logging

# Configurazione del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    def __init__(self, message):
        self.message = message
        self.command = type('Command', (), {'name': 'draft'})()
        self.prefix = "!"
        self.author = message.author
        self.send = message.channel.send

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
        # Test con contenuti di diverse lunghezze
        test_contents = [
            # Test 1: Contenuto breve
            "Configurazione base di un server web Apache",
            
            # Test 2: Contenuto medio
            """Configurazione di un server web Apache su Ubuntu 22.04
            
            Questo articolo coprirà:
            1. Installazione di Apache
            2. Configurazione base
            3. Gestione dei virtual host
            4. Sicurezza e best practices""",
            
            # Test 3: Contenuto lungo
            "Test" * 2000  # Circa 8000 caratteri
        ]
        
        ai_handler = AIHandler()
        wp_handler = WordPressHandler()
        
        for i, content in enumerate(test_contents, 1):
            print(f"\nTest {i}:")
            print("-" * 50)
            
            # Crea il file di test
            filename = f"test_article_{i}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            try:
                # Avvia il server mock
                runner = await start_mock_server(content)
                
                try:
                    # Crea un mock del messaggio con allegato
                    message = MockMessage(
                        content="!draft",
                        attachments=[MockAttachment(filename, content)]
                    )
                    
                    # Crea il contesto
                    ctx = MockContext(message)
                    
                    print("\nFase 1: Estrazione argomento")
                    print("-" * 30)
                    success, argument = await extract_command_argument(ctx)
                    
                    if success:
                        print("✅ Estrazione argomento riuscita!")
                        print(f"Contenuto estratto: {str(argument)[:100]}...")
                        
                        print("\nFase 2: Generazione articolo")
                        print("-" * 30)
                        success, message, generated_content = await ai_handler.generate_article(argument)
                        
                        if success:
                            print("✅ Generazione articolo riuscita!")
                            print(f"Lunghezza contenuto generato: {len(generated_content)} caratteri")
                            
                            print("\nFase 3: Creazione bozza WordPress")
                            print("-" * 30)
                            success, message, draft_url = await wp_handler.create_draft(str(argument), generated_content)
                            
                            if success:
                                print("✅ Creazione bozza riuscita!")
                                print(f"URL bozza: {draft_url}")
                            else:
                                print(f"❌ Errore nella creazione della bozza: {message}")
                        else:
                            print(f"❌ Errore nella generazione: {message}")
                    else:
                        print(f"❌ Errore nell'estrazione: {argument}")
                        
                finally:
                    # Ferma il server mock
                    await runner.cleanup()
                    
            finally:
                # Pulisci il file di test
                if os.path.exists(filename):
                    os.remove(filename)
            
            print("\n" + "="*50 + "\n")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_draft_with_file()) 