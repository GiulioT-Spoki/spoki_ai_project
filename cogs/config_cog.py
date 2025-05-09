# ==========================================================
# config_cog.py
# Descrizione: Cog che gestisce la configurazione dinamica del bot tramite comandi Discord. Permette di visualizzare e modificare i parametri principali (articoli e video correlati, canali, dominio) e di mostrare lo stato attuale tramite embed.
# Dipendenze principali: discord.ext.commands, logging, json, config/config.json, config/messages.json, utils.youtube_handler.
# Flusso di lavoro: Caricato all'avvio dal bot principale, espone i comandi !status, !setrelatedarticles e !setrelatedvideos. Interagisce con la configurazione e aggiorna i parametri in tempo reale.
# ==========================================================
import discord
from discord.ext import commands
import logging
import json
import os
from datetime import datetime
from utils.youtube_handler import YouTubeHandler

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        # Carica le configurazioni
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
        
        # Carica i messaggi di cortesia
        with open('config/messages.json', 'r') as f:
            self.messages = json.load(f)
        
        # Inizializza l'handler di YouTube
        self.youtube_handler = YouTubeHandler()

    def _backup_config(self):
        """Crea un backup del file di configurazione."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f'config/config_backup_{timestamp}.json'
        try:
            with open('config/config.json', 'r') as source:
                with open(backup_path, 'w') as backup:
                    backup.write(source.read())
            self.logger.info(f"Backup della configurazione creato: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Errore durante il backup della configurazione: {str(e)}")
            return False

    def _save_config(self):
        """Salva la configurazione nel file."""
        try:
            # Crea un backup prima di salvare
            if not self._backup_config():
                return False, "Impossibile creare il backup della configurazione"
            
            # Salva la nuova configurazione
            with open('config/config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            return True, "Configurazione salvata con successo"
        except Exception as e:
            error_msg = f"Errore durante il salvataggio della configurazione: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    @commands.command(name="setrelatedarticles")
    async def set_related_articles(self, ctx, count: int = None):
        """
        Imposta il numero massimo di articoli correlati da aggiungere agli articoli generati.
        Se non viene specificato un numero, mostra il valore attuale.
        """
        self.logger.info(f"Comando !setrelatedarticles ricevuto da {ctx.author} con valore: {count}")
        
        try:
            # Se non viene specificato un numero, mostra il valore attuale
            if count is None:
                current_count = self.config['commands']['draft']['related_content']['max_articles']
                await ctx.send(self.messages["setrelatedarticles_current"].format(count=current_count))
                return
            
            # Valida il numero
            if not 1 <= count <= 10:
                await ctx.send(self.messages["setrelatedarticles_invalid"])
                return
            
            # Aggiorna la configurazione
            self.config['commands']['draft']['related_content']['max_articles'] = count
            
            # Salva la configurazione
            success, message = self._save_config()
            if not success:
                await ctx.send(self.messages["setrelatedarticles_error"].format(error=message))
                return
            
            self.logger.info(f"Numero di articoli correlati aggiornato a {count}")
            await ctx.send(self.messages["setrelatedarticles_success"].format(count=count))
            
        except Exception as e:
            error_msg = self.messages["setrelatedarticles_error"].format(error=str(e))
            self.logger.error(f"{error_msg}\nStack trace:", exc_info=True)
            await ctx.send(error_msg)

    @commands.command(name="setrelatedvideos")
    async def set_related_videos(self, ctx, count: int = None):
        """
        Imposta il numero massimo di video correlati da aggiungere agli articoli generati.
        Se non viene specificato un numero, mostra il valore attuale.
        """
        self.logger.info(f"Comando !setrelatedvideos ricevuto da {ctx.author} con valore: {count}")
        
        try:
            # Se non viene specificato un numero, mostra il valore attuale
            if count is None:
                current_count = self.config['commands']['draft']['related_content']['max_videos']
                await ctx.send(self.messages["setrelatedvideos_current"].format(count=current_count))
                return
            
            # Valida il numero
            if not 1 <= count <= 10:
                await ctx.send(self.messages["setrelatedvideos_invalid"])
                return
            
            # Aggiorna la configurazione
            self.config['commands']['draft']['related_content']['max_videos'] = count
            
            # Salva la configurazione
            success, message = self._save_config()
            if not success:
                await ctx.send(self.messages["setrelatedvideos_error"].format(error=message))
                return
            
            self.logger.info(f"Numero di video correlati aggiornato a {count}")
            await ctx.send(self.messages["setrelatedvideos_success"].format(count=count))
            
        except Exception as e:
            error_msg = self.messages["setrelatedvideos_error"].format(error=str(e))
            self.logger.error(f"{error_msg}\nStack trace:", exc_info=True)
            await ctx.send(error_msg)

    @commands.command(name="status")
    async def status(self, ctx):
        """
        Mostra lo stato attuale delle configurazioni del bot.
        """
        self.logger.info(f"Comando !status ricevuto da {ctx.author}")
        
        try:
            # Ottieni il nome del canale YouTube
            channel_id = self.config['youtube']['channel_id']
            success, channel_info = await self.youtube_handler.get_channel_info(channel_id)
            
            if not success:
                self.logger.error(f"Errore nel recupero delle informazioni del canale: {channel_info}")
                channel_name = "Errore nel recupero"
            else:
                channel_name = channel_info['title']
            
            # Prepara il dominio WordPress senza https://
            wp_domain_full = self.config['wordpress']['domain']
            wp_domain_clean = wp_domain_full.replace('https://', '').replace('http://', '')
            
            # Crea l'embed usando i nomi dei campi da messages.json
            embed = discord.Embed(
                title=self.messages["status_title"],
                color=discord.Color.blue()
            )
            embed.add_field(
                name=self.messages["status_field_articles"],
                value=str(self.config['commands']['draft']['related_content']['max_articles']),
                inline=False
            )
            embed.add_field(
                name=self.messages["status_field_videos"],
                value=str(self.config['commands']['draft']['related_content']['max_videos']),
                inline=False
            )
            embed.add_field(
                name=self.messages["status_field_youtube"],
                value=f"[{channel_name}](https://www.youtube.com/channel/{channel_id})",
                inline=False
            )
            embed.add_field(
                name=self.messages["status_field_wordpress"],
                value=f"[{wp_domain_clean}]({wp_domain_full})",
                inline=False
            )
            await ctx.send(embed=embed)
            self.logger.info("Stato del bot inviato con successo (embed)")
            
        except Exception as e:
            error_msg = f"❌ Errore durante il recupero dello stato: {str(e)}"
            self.logger.error(f"{error_msg}\nStack trace:", exc_info=True)
            await ctx.send(error_msg)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot)) 