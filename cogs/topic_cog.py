# ==========================================================
# topic_cog.py
# Descrizione: Cog che gestisce la ricerca di documenti/articoli tramite il comando !topic, creando thread Discord dedicati e mostrando i risultati tramite embed.
# Dipendenze principali: discord.ext.commands, utils.wordpress_handler, utils.command_utils, config/config.json, config/messages.json, logging, html, re.
# Flusso di lavoro: Caricato all'avvio dal bot principale, espone il comando !topic. Interagisce con WordPress per la ricerca e con Discord per la creazione di thread e la visualizzazione dei risultati.
# ==========================================================
import discord
from discord.ext import commands
from utils.wordpress_handler import WordPressHandler
from utils.command_utils import extract_command_argument
import logging
import html
import re
import json

class TopicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wp_handler = WordPressHandler()
        self.logger = logging.getLogger(__name__)
        
        # Load config
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
        
        # Carica i messaggi di cortesia
        with open('config/messages.json', 'r') as f:
            self.messages = json.load(f)
        
        # Discord limits from config
        self.DISCORD_MESSAGE_LIMIT = self.config['discord']['message_limit']
        self.DISCORD_THREAD_TITLE_LIMIT = self.config['discord']['thread_title_limit']
        self.MAX_RESULTS_PER_EMBED = self.config['discord']['max_results_per_embed']

    @commands.command(name="topic")
    async def topic(self, ctx, *, search_term=None):
        self.logger.info(f"Comando !topic ricevuto da {ctx.author} con ricerca: {search_term}")
        
        # Usa la funzione centralizzata per estrarre l'argomento
        success, search_term = await extract_command_argument(ctx)
        if not success or not search_term or not search_term.strip():
            await ctx.send(self.messages["topic_missing_input"])
            self.logger.info("Nessun argomento fornito: ricerca non eseguita.")
            return

        # Creare un thread per questa ricerca
        thread_name = f"Ricerca: {search_term[:self.DISCORD_THREAD_TITLE_LIMIT - 10]}"  # -10 per "Ricerca: "
        thread = await ctx.message.create_thread(
            name=thread_name,
            auto_archive_duration=self.config.get('thread_archive_duration', 60)
        )
        self.logger.info(f"Thread creato per la ricerca '{search_term}'")

        # Inviare il messaggio iniziale nel thread
        processing_msg = await thread.send(f"🔍 Sto cercando documenti relativi a: {search_term}")

        # Eseguire la ricerca
        success, results = await self.wp_handler.search_docs(search_term)
        
        if success and isinstance(results, list):
            if not results:
                self.logger.info(f"Ricerca completata per '{search_term}' - Nessun risultato trovato")
                await processing_msg.edit(content=self.messages["topic_no_results"])
                return

            # Log dei risultati trovati
            total_results = len(results)
            self.logger.info(f"Ricerca completata per '{search_term}' - Trovati {total_results} risultati")
            
            # Messaggio iniziale con il numero totale di risultati
            await processing_msg.edit(content=self.messages["topic_results_found"].format(
                total_results=total_results,
                search_term=search_term
            ))

            # Suddividi i risultati in gruppi per embed
            for start_idx in range(0, total_results, self.MAX_RESULTS_PER_EMBED):
                end_idx = min(start_idx + self.MAX_RESULTS_PER_EMBED, total_results)
                current_batch = results[start_idx:end_idx]
                
                # Prepara la descrizione per questo gruppo
                description = []
                for i, doc in enumerate(current_batch, start=start_idx + 1):
                    title = html.unescape(re.sub('<[^<]+?>', '', doc['title']))
                    result_line = f"{i}. [{title}]({doc['link']})"
                    description.append(result_line)
                    self.logger.info(f"Risultato {i}: {title} - {doc['link']}")

                # Crea e invia l'embed per questo gruppo
                embed = discord.Embed(
                    title=f"Risultati {start_idx + 1}-{end_idx} di {total_results}",
                    description="\n".join(description),
                    color=discord.Color.blue()
                )
                await thread.send(embed=embed)

            # Aggiungere un messaggio di follow-up nel thread
            await thread.send(self.messages["topic_follow_up"])
        else:
            error_message = results if isinstance(results, str) else "Si è verificato un errore durante la ricerca."
            self.logger.error(f"Errore durante la ricerca di '{search_term}': {error_message}")
            await processing_msg.edit(content=f"❌ {error_message}")

async def setup(bot):
    await bot.add_cog(TopicCog(bot))