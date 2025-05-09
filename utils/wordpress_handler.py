# ==========================================================
# wordpress_handler.py
# Descrizione: Gestisce la comunicazione con l'API REST di WordPress per la ricerca di documenti/articoli e la creazione di draft tramite BetterDocs. Si occupa di autenticazione, paginazione e formattazione risultati.
# Dipendenze principali: cloudscraper, dotenv, logging, config/config.json, os, json.
# Flusso di lavoro: Invocato dai cog (topic_cog, draft_cog) per cercare documenti e creare draft su WordPress.
# ==========================================================
import cloudscraper
import os
from dotenv import load_dotenv
import json
import logging

logger = logging.getLogger(__name__)

class WordPressHandler:
    def __init__(self):
        load_dotenv()
        self.site_url = os.getenv('WP_API_URL')
        self.username = os.getenv('WP_USERNAME')
        self.app_password = os.getenv('WP_APP_PASSWORD')
        self.scraper = cloudscraper.create_scraper()
        
        # Load config
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
        self.per_page = self.config['wordpress']['results_per_page']
        
    async def test_connection(self):
        try:
            # Configurazione dell'autenticazione Basic
            auth = (self.username, self.app_password)
            
            # Tentativo di fare una richiesta GET all'endpoint
            response = self.scraper.get(
                self.site_url,
                auth=auth
            )
            
            if response.status_code == 200:
                return True, "Connessione a WordPress riuscita!"
            else:
                return False, f"Errore nella connessione: Status code {response.status_code}"
                
        except Exception as e:
            return False, f"Errore nella connessione: {str(e)}"

    async def search_docs(self, search_term):
        try:
            auth = (self.username, self.app_password)
            formatted_results = []
            page = 1
            
            while True:
                # Costruzione dell'URL con paginazione
                search_url = f"{self.site_url}?search={search_term}&per_page={self.per_page}&page={page}"
                
                # Esecuzione della ricerca
                response = self.scraper.get(
                    search_url,
                    auth=auth
                )
                
                if response.status_code == 200:
                    results = response.json()
                    if not results:
                        break  # Nessun altro risultato disponibile
                        
                    # Aggiunge i risultati di questa pagina
                    for doc in results:
                        formatted_results.append({
                            'title': doc.get('title', {}).get('rendered', ''),
                            'link': doc.get('link', ''),
                            'excerpt': doc.get('excerpt', {}).get('rendered', '')
                        })
                    
                    # Controlla se ci sono altre pagine
                    total_pages = int(response.headers.get('X-WP-TotalPages', '1'))
                    if page >= total_pages:
                        break
                        
                    page += 1
                elif response.status_code == 400:
                    # La pagina richiesta non esiste, abbiamo finito
                    break
                else:
                    return False, f"Errore nella ricerca: Status code {response.status_code}"
            
            if formatted_results:
                return True, formatted_results
            else:
                return False, "Nessun documento trovato per questo argomento."
                
        except Exception as e:
            return False, f"Errore durante la ricerca: {str(e)}"

    async def create_draft(self, title, content):
        """
        Crea una bozza su WordPress usando l'API REST di BetterDocs.
        
        Args:
            title (str): Titolo dell'articolo
            content (str): Contenuto dell'articolo
            
        Returns:
            tuple: (success, message, url)
                - success (bool): True se la creazione è riuscita
                - message (str): Messaggio di successo o errore
                - url (str): URL della bozza creata (None in caso di errore)
        """
        try:
            if not all([self.site_url, self.username, self.app_password]):
                return False, "Configurazione WordPress incompleta. Verifica le variabili d'ambiente.", None

            # Costruisci l'endpoint corretto per BetterDocs
            base_url = self.site_url.rstrip('/')
            
            # Rimuovi eventuali /docs finali
            if base_url.endswith('/docs'):
                base_url = base_url[:-5]
            
            # Se l'URL non contiene già wp-json, aggiungilo
            if '/wp-json' not in base_url:
                endpoint = f"{base_url}/wp-json/wp/v2/docs"
            else:
                # Se contiene già wp-json, aggiungi solo il tipo di post
                endpoint = f"{base_url}/docs"
            
            logger.debug(f"Creazione bozza su endpoint: {endpoint}")
            
            # Prepara i dati per la richiesta
            data = {
                'title': title,
                'content': content,
                'status': 'draft'  # Crea come bozza
            }
            
            # Configurazione dell'autenticazione Basic
            auth = (self.username, self.app_password)
            
            # Esegui la richiesta POST
            response = self.scraper.post(
                endpoint,
                json=data,
                auth=auth
            )
            
            if response.status_code in [200, 201]:
                post_data = response.json()
                post_url = post_data.get('link', '')
                return True, "✅ Bozza creata con successo!", post_url
            else:
                error_msg = f"❌ Errore nella creazione della bozza: Status code {response.status_code}"
                logger.error(f"{error_msg}\nResponse: {response.text}")
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"❌ Errore durante la creazione della bozza: {str(e)}"
            logger.error(f"{error_msg}\nStack trace:", exc_info=True)
            return False, error_msg, None