# ==========================================================
# ai_handler.py
# Descrizione: Gestisce la comunicazione asincrona con l'API OpenAI/ChatGPT per la generazione di articoli e risposte. Carica e valida la configurazione AI e i prompt.
# Dipendenze principali: openai, dotenv, logging, config/config.json, config/prompts.json, asyncio, os, json.
# Flusso di lavoro: Invocato dai cog (soprattutto draft_cog) per generare contenuti tramite AI, stimare token e gestire i prompt dinamicamente.
# ==========================================================
import os
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
import logging
import asyncio

# Configurazione del logger
logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        load_dotenv()
        self.load_config()
        api_key = os.getenv('AI_API_KEY')
        if not api_key:
            raise ValueError("AI_API_KEY non trovata nelle variabili d'ambiente")
        self.client = AsyncOpenAI(api_key=api_key)
        self.load_prompts()

    def load_config(self):
        try:
            with open('config/config.json', 'r') as f:
                config = json.load(f)
                self.model = config.get('ai', {}).get('model', 'gpt-3.5-turbo')
                self.temperature = config.get('ai', {}).get('temperature', 0.7)
                self.max_tokens_ratio = config.get('ai', {}).get('max_tokens_ratio', 0.8)
                self.token_limits = config.get('ai', {}).get('token_limits', {
                    'gpt-3.5-turbo': 4096,
                    'gpt-4': 8192,
                    'gpt-4-32k': 32768
                })
        except Exception as e:
            logger.error(f"Errore nel caricamento della configurazione: {str(e)}")
            # Valori di default
            self.model = 'gpt-3.5-turbo'
            self.temperature = 0.7
            self.max_tokens_ratio = 0.8
            self.token_limits = {
                'gpt-3.5-turbo': 4096,
                'gpt-4': 8192,
                'gpt-4-32k': 32768
            }

    def load_prompts(self):
        try:
            with open('config/prompts.json', 'r') as f:
                self.prompts = json.load(f)
            logger.info("Prompt caricati correttamente")
        except Exception as e:
            logger.error(f"Errore nel caricamento dei prompt: {str(e)}")
            self.prompts = {}

    async def reload_prompts(self):
        """Ricarica i prompt da file."""
        try:
            with open('config/prompts.json', 'r') as f:
                self.prompts = json.load(f)
            logger.info("Prompt ricaricati correttamente")
            return True, "Prompt ricaricati con successo"
        except Exception as e:
            logger.error(f"Errore nel ricaricamento dei prompt: {str(e)}")
            return False, f"Errore nel ricaricamento dei prompt: {str(e)}"

    def estimate_tokens(self, text: str) -> int:
        # Stima approssimativa: 1 token ≈ 4 caratteri in italiano
        return len(text) // 4

    async def generate_article(self, topic: str, content: str = "") -> str:
        """
        Genera un articolo usando OpenAI basato sul topic fornito.
        
        Args:
            topic (str): Il topic o le istruzioni per l'articolo
            content (str, optional): Il contenuto del file allegato, se presente
        
        Returns:
            str: L'articolo generato
        """
        try:
            # Ricarica i prompt prima di ogni generazione
            await self.reload_prompts()
            
            # Ottieni il template
            template = self.prompts['article_generation']['template']
            
            # Formatta il template con topic e content
            formatted_prompt = template.format(
                topic=str(topic),
                content=str(content)
            )
            
            # Stima il numero di token
            estimated_tokens = self.estimate_tokens(formatted_prompt)
            model_limit = self.token_limits[self.model]
            
            # Calcola i token rimanenti per la risposta, lasciando un margine di sicurezza del 10%
            remaining_tokens = int((model_limit - estimated_tokens) * 0.9)
            logger.debug(f"Token stimati: {estimated_tokens}, Limite modello: {model_limit}, Token per risposta: {remaining_tokens}")
            
            if estimated_tokens > model_limit * 0.9:  # Se il prompt usa più del 90% dei token
                logger.error(f"Prompt troppo lungo: {estimated_tokens} tokens > {model_limit * 0.9} limite")
                raise Exception(f"Il prompt è troppo lungo per il modello {self.model} (stimati {estimated_tokens} tokens, limite {int(model_limit * 0.9)})")

            # Chiamata all'API OpenAI con la nuova interfaccia asincrona
            try:
                logger.debug(f"Chiamata a OpenAI con modello {self.model}...")
                
                # Imposta un timeout di 120 secondi (2 minuti)
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "Sei un assistente esperto nella scrittura di documentazione tecnica."},
                            {"role": "user", "content": formatted_prompt}
                        ],
                        temperature=self.temperature,
                        max_tokens=remaining_tokens
                    ),
                    timeout=120.0
                )
                
                logger.debug("Risposta ricevuta da OpenAI")
                
                if response and response.choices:
                    generated_content = response.choices[0].message.content
                    logger.info(f"Articolo generato ({len(generated_content)} caratteri)")
                    return generated_content
                else:
                    logger.error("Nessuna risposta generata dal modello")
                    raise Exception("Nessuna risposta generata dal modello")
                    
            except asyncio.TimeoutError:
                logger.error("Timeout durante la chiamata a OpenAI")
                raise Exception("La generazione dell'articolo ha impiegato troppo tempo. Riprova più tardi.")
            except Exception as e:
                logger.error(f"Errore durante la chiamata all'API di ChatGPT: {str(e)}", exc_info=True)
                raise Exception(f"Errore durante la generazione: {str(e)}")
            
        except Exception as e:
            logger.error(f"Errore nella generazione dell'articolo: {str(e)}", exc_info=True)
            raise Exception(f"Errore nella generazione dell'articolo: {str(e)}")