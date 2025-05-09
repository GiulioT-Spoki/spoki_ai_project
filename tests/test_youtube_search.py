import asyncio
import logging
from utils.youtube_handler import YouTubeHandler

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_youtube_search():
    """Testa la ricerca di video su YouTube."""
    try:
        # Crea un'istanza di YouTubeHandler
        youtube_handler = YouTubeHandler()
        
        # Lista di keywords di test
        test_keywords = ["whatsapp", "spoki", "messaging"]
        
        # Testa la ricerca
        success, results = await youtube_handler.search_videos(test_keywords)
        
        if success:
            print(f"✅ Test riuscito: trovati {len(results)} video")
            print("\nVideo trovati:")
            for video in results:
                print(f"\n- {video['title']}")
                print(f"  URL: {video['url']}")
                print(f"  Pubblicato il: {video['published_at']}")
        else:
            print(f"❌ Test fallito: {results}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {str(e)}")

if __name__ == "__main__":
    # Esegui il test
    asyncio.run(test_youtube_search()) 