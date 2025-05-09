import asyncio
import logging
from utils.youtube_handler import YouTubeHandler

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_youtube_connection():
    """Testa la connessione all'API di YouTube."""
    try:
        # Crea un'istanza di YouTubeHandler
        youtube_handler = YouTubeHandler()
        
        # Testa la connessione
        success, message = await youtube_handler.test_connection()
        
        if success:
            print(f"✅ Test riuscito: {message}")
        else:
            print(f"❌ Test fallito: {message}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {str(e)}")

if __name__ == "__main__":
    # Esegui il test
    asyncio.run(test_youtube_connection()) 