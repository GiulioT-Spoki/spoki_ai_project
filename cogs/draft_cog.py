# ==========================================================
# draft_cog.py
# Descrizione: Cog che gestisce la generazione di articoli tramite AI, la ricerca e l'inserimento di articoli e video correlati, e la creazione di draft su WordPress. Espone il comando !draft e la ricarica dei prompt.
# Dipendenze principali: discord.ext.commands, cloudscraper, utils.ai_handler, utils.wordpress_handler, utils.youtube_handler, utils.command_utils, config/config.json, config/messages.json, logging, asyncio, re, os.
# Flusso di lavoro: Caricato all'avvio dal bot principale, espone il comando !draft e !reloadprompts. Interagisce con l'AI, WordPress e YouTube per generare contenuti e suggerimenti.
# ==========================================================
import discord
from discord.ext import commands
import cloudscraper
from utils.ai_handler import AIHandler
from utils.wordpress_handler import WordPressHandler
from utils.youtube_handler import YouTubeHandler
from utils.command_utils import extract_command_argument
import logging
import os
import asyncio
import re
import json

class DraftCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scraper = cloudscraper.create_scraper()
        self.ai_handler = AIHandler()
        self.wp_handler = WordPressHandler()
        self.youtube_handler = YouTubeHandler()
        self.logger = logging.getLogger(__name__)
        
        # Carica le configurazioni
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
        
        # Carica i messaggi di cortesia
        with open('config/messages.json', 'r') as f:
            self.messages = json.load(f)
        
        # Estrai i limiti per i contenuti correlati
        self.max_articles = self.config['commands']['draft']['related_content']['max_articles']
        self.max_videos = self.config['commands']['draft']['related_content']['max_videos']

    @commands.command(name="reloadprompts")
    async def reload_prompts(self, ctx):
        """Ricarica i prompt da file."""
        self.logger.info(f"Comando !reloadprompts ricevuto da {ctx.author}")
        success, message = await self.ai_handler.reload_prompts()
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")

    @commands.command(name="draft")
    async def draft(self, ctx, *, content=None):
        self.logger.info(f"Comando !draft ricevuto da {ctx.author}")
        
        # Usa la funzione centralizzata per estrarre l'argomento
        success, content = await extract_command_argument(ctx)
        if not success or not content or not content.strip():
            await ctx.send(self.messages["draft_missing_input"])
            self.logger.info("Nessun argomento o allegato fornito: richiesta non inviata all'AI.")
            return

        # Invia il messaggio di elaborazione
        processing_msg = await ctx.send(self.messages["draft_processing"])
        
        try:
            # Genera l'articolo usando l'AI
            self.logger.debug(f"Inizio generazione articolo con content: {content[:100]}...")
            generated_content = await self.ai_handler.generate_article("", content)
            self.logger.info("Articolo generato con successo")

            # Estrai le keywords dal blocco SEO
            keywords_match = re.search(r'<!-- KEYWORDS -->\n(.*?)\n\n<!-- META DESCRIPTION -->', generated_content, re.DOTALL)
            self.logger.info(f"Pattern di ricerca keywords: <!-- KEYWORDS -->\n(.*?)\n\n<!-- META DESCRIPTION -->")
            self.logger.info(f"Contenuto generato: {generated_content[:500]}...")  # Log dei primi 500 caratteri
            
            if keywords_match:
                keywords_text = keywords_match.group(1)
                self.logger.info(f"Testo keywords trovato: {keywords_text}")
                # Estrai le keywords (rimuovi i trattini e gli spazi)
                keywords = [k.strip('- ').strip() for k in keywords_text.split('\n') if k.strip()]
                self.logger.info(f"Keywords estratte: {keywords}")

                # Cerca articoli correlati per ogni keyword
                related_articles = []
                for keyword in keywords:
                    self.logger.info(f"Cercando articoli per keyword: {keyword}")
                    success, results = await self.wp_handler.search_docs(keyword)
                    if success and isinstance(results, list):
                        self.logger.info(f"Trovati {len(results)} risultati per '{keyword}'")
                        # Aggiungi i risultati alla lista, evitando duplicati
                        for result in results:
                            if result not in related_articles:
                                related_articles.append(result)
                                if len(related_articles) >= self.max_articles:
                                    break
                    if len(related_articles) >= self.max_articles:
                        break

                # Cerca video correlati
                self.logger.info(f"Cercando video per keywords: {keywords}")
                success, videos = await self.youtube_handler.search_videos(keywords, max_results=self.max_videos)
                if success and videos:
                    self.logger.info(f"Trovati {len(videos)} video correlati")
                    await processing_msg.edit(content=f"{processing_msg.content}\n{self.messages['draft_related_videos_found'].format(count=len(videos))}")
                else:
                    self.logger.info("Nessun video correlato trovato")
                    await processing_msg.edit(content=f"{processing_msg.content}\n{self.messages['draft_no_related_videos']}")

                # Aggiungi la sezione "Articoli correlati" all'articolo
                if related_articles:
                    related_section = "\n\n<!-- wp:heading -->\n<h2>Articoli correlati</h2>\n<!-- /wp:heading -->\n\n<!-- wp:list -->\n<ul>"
                    for article in related_articles[:self.max_articles]:  # Usa il limite dalla configurazione
                        title = re.sub('<[^<]+?>', '', article['title'])  # Rimuovi tag HTML
                        related_section += f"\n<li><a href=\"{article['link']}\">{title}</a></li>"
                    related_section += "\n</ul>\n<!-- /wp:list -->"
                    
                    # Inserisci la sezione prima del blocco SEO
                    generated_content = generated_content.replace('<!-- wp:html -->', f"{related_section}\n\n<!-- wp:html -->")
                    self.logger.info(f"Aggiunti {len(related_articles)} articoli correlati")

                # Aggiungi la sezione "Video correlati" se ci sono video
                if success and videos:
                    videos_section = "\n\n<!-- wp:heading -->\n<h2>Video correlati</h2>\n<!-- /wp:heading -->\n\n<!-- wp:list -->\n<ul>"
                    for video in videos[:self.max_videos]:  # Usa il limite dalla configurazione
                        videos_section += f"\n<li><a href=\"{video['url']}\">{video['title']}</a></li>"
                    videos_section += "\n</ul>\n<!-- /wp:list -->"
                    
                    # Inserisci la sezione prima del blocco SEO
                    generated_content = generated_content.replace('<!-- wp:html -->', f"{videos_section}\n\n<!-- wp:html -->")
                    self.logger.info(f"Aggiunti {len(videos)} video correlati")

            # Estrai il titolo dal primo header <h1> o <h2>
            match = re.search(r'<h1>(.*?)</h1>|<h2>(.*?)</h2>', generated_content, re.IGNORECASE)
            if match:
                title = match.group(1) if match.group(1) else match.group(2)
            else:
                title = content.split('\n')[0][:100]  # Usa la prima riga come titolo, massimo 100 caratteri
                if not title:
                    title = "Nuovo articolo"  # Titolo di default se non c'è contenuto
            
            self.logger.debug(f"Titolo estratto: {title}")

            # Crea il draft
            success, message, url = await self.wp_handler.create_draft(title=title, content=generated_content)
            
            if success:
                await processing_msg.edit(content=f"{self.messages['draft_success']} Puoi visualizzarlo qui: {url}")
                self.logger.info(f"Draft creato con successo: {url}")
            else:
                await processing_msg.edit(content=f"❌ {message}")
                self.logger.error(f"Errore durante la creazione del draft: {message}")

        except Exception as e:
            error_msg = self.messages["draft_ai_error"].format(error=str(e))
            self.logger.error(f"{error_msg}\nStack trace:", exc_info=True)
            await processing_msg.edit(content=error_msg)

async def setup(bot):
    await bot.add_cog(DraftCog(bot))