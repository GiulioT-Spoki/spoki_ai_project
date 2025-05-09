# ==========================================================
# youtube_handler.py
# Descrizione: Gestisce la comunicazione con l'API di YouTube per recuperare informazioni sul canale e cercare video tramite keywords. Si occupa di autenticazione e parsing dei risultati.
# Dipendenze principali: googleapiclient, dotenv, logging, config/config.json, os, json.
# Flusso di lavoro: Invocato dai cog (config_cog, draft_cog) per mostrare info canale e suggerire video correlati.
# ==========================================================
import os
from dotenv import load_dotenv
import googleapiclient.discovery
import logging
import json
from googleapiclient.errors import HttpError

class YouTubeHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        
        # Carica la configurazione
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
        
        # Inizializza l'API di YouTube
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", developerKey=os.getenv('YOUTUBE_API_KEY')
        )
        self.channel_id = self.config['youtube']['channel_id']
        
        self.logger.info("YouTubeHandler inizializzato con successo")

    async def get_channel_info(self, channel_id):
        """
        Ottiene le informazioni di un canale YouTube dato il suo ID.
        
        Args:
            channel_id (str): L'ID del canale YouTube
            
        Returns:
            tuple: (success, result)
                - success (bool): True se la richiesta è andata a buon fine
                - result (dict/str): Dizionario con le informazioni del canale o messaggio di errore
        """
        try:
            self.logger.info(f"Richiesta informazioni per il canale: {channel_id}")
            
            # Esegui la richiesta all'API
            request = self.youtube.channels().list(
                part="snippet,statistics",
                id=channel_id
            )
            response = request.execute()
            
            # Verifica se il canale esiste
            if not response['items']:
                error_msg = f"Canale non trovato: {channel_id}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Estrai le informazioni rilevanti
            channel_info = {
                'id': channel_id,
                'title': response['items'][0]['snippet']['title'],
                'description': response['items'][0]['snippet']['description'],
                'subscriber_count': response['items'][0]['statistics']['subscriberCount'],
                'video_count': response['items'][0]['statistics']['videoCount']
            }
            
            self.logger.info(f"Informazioni del canale recuperate con successo: {channel_info['title']}")
            return True, channel_info
            
        except HttpError as e:
            error_msg = f"Errore API YouTube: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Errore durante il recupero delle informazioni del canale: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    async def search_videos(self, keywords, max_results=5):
        """
        Cerca video nel canale specificato usando le keywords fornite.
        
        Args:
            keywords (list): Lista di keywords per la ricerca
            max_results (int): Numero massimo di risultati da restituire
            
        Returns:
            tuple: (success, results)
                - success (bool): True se la ricerca è andata a buon fine
                - results (list/str): Lista di video trovati o messaggio di errore
        """
        try:
            self.logger.info(f"Ricerca video per keywords: {keywords}")
            
            # Combina le keywords in una singola stringa di ricerca
            search_query = " ".join(keywords)
            
            # Esegui la ricerca
            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                q=search_query,
                type="video",
                maxResults=max_results,
                order="relevance"
            )
            response = request.execute()
            
            # Estrai i video trovati
            videos = []
            for item in response.get('items', []):
                video = {
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                }
                videos.append(video)
            
            self.logger.info(f"Trovati {len(videos)} video")
            return True, videos
            
        except HttpError as e:
            error_msg = f"Errore API YouTube: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Errore durante la ricerca dei video: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg 