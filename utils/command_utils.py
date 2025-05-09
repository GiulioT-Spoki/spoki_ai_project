# ==========================================================
# command_utils.py
# Descrizione: Funzioni e classi di utilità per l'estrazione, validazione e pulizia degli argomenti dei comandi Discord. Gestisce anche la lettura di allegati e messaggi di riferimento.
# Dipendenze principali: discord, discord.ext.commands, config/config.json, config/messages.json, logging, re, aiohttp, json.
# Flusso di lavoro: Invocato da tutti i cog che devono estrarre o validare argomenti da messaggi, allegati o thread Discord.
# ==========================================================

import discord
from discord.ext import commands
from typing import Optional, Tuple, Dict, Any
import logging
import re
import json
import aiohttp

# Configurazione del logger
logger = logging.getLogger(__name__)

# Carica i messaggi di cortesia
with open('config/messages.json', 'r') as f:
    messages = json.load(f)

class CommandArgumentError(Exception):
    """Eccezione personalizzata per errori nell'estrazione degli argomenti"""
    pass

class Content:
    """Classe per gestire il contenuto estratto da file"""
    def __init__(self, content: str):
        self._content = content
        self._from_file = True
    
    def __str__(self) -> str:
        return self._content
    
    def __len__(self) -> int:
        return len(self._content)

class CommandValidator:
    """Classe per la validazione degli argomenti dei comandi"""
    
    def __init__(self):
        # Carica la configurazione
        with open('config/config.json', 'r') as f:
            self.config = json.load(f)
    
    def validate_topic_argument(self, argument: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un argomento per il comando !topic
        
        Args:
            argument: L'argomento da validare
            
        Returns:
            Tuple[bool, Optional[str]]: (successo, messaggio_errore)
        """
        limits = self.config['commands']['topic']
        if len(argument) < limits['min_length']:
            return False, f"L'argomento deve essere di almeno {limits['min_length']} caratteri"
        if len(argument) > limits['max_length']:
            return False, f"L'argomento non può superare i {limits['max_length']} caratteri"
        return True, None
    
    def validate_draft_argument(self, argument: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un argomento per il comando !draft
        
        Args:
            argument: L'argomento da validare
            
        Returns:
            Tuple[bool, Optional[str]]: (successo, messaggio_errore)
        """
        # Per il comando draft, la validazione della lunghezza viene fatta solo se l'argomento
        # non viene da un file .txt
        if not hasattr(argument, '_from_file'):
            limits = self.config['commands']['draft']
            if len(argument) < limits['min_length']:
                return False, f"L'argomento deve essere di almeno {limits['min_length']} caratteri"
            if len(argument) > limits['max_length']:
                return False, f"L'argomento non può superare i {limits['max_length']} caratteri"
        return True, None

def clean_content(content: str) -> str:
    """
    Pulisce il contenuto da prefissi e formattazioni indesiderate.
    
    Args:
        content: Il contenuto da pulire
        
    Returns:
        str: Il contenuto pulito
    """
    # Rimuovi spazi all'inizio e alla fine
    content = content.strip()
    
    # Rimuovi prefissi comuni
    prefixes = ['>>', '>', '>>>', '```', '``', '`']
    for prefix in prefixes:
        if content.startswith(prefix):
            content = content[len(prefix):].strip()
    
    # Rimuovi suffissi comuni
    suffixes = ['```', '``', '`']
    for suffix in suffixes:
        if content.endswith(suffix):
            content = content[:-len(suffix)].strip()
    
    # Rimuovi formattazione Discord
    content = re.sub(r'[*_~`]', '', content)
    
    return content

async def get_reference_content(ctx) -> Tuple[bool, Optional[str], Optional[discord.Message]]:
    """
    Recupera il contenuto dal messaggio di riferimento, se presente.
    
    Args:
        ctx: Il contesto del comando Discord
        
    Returns:
        Tuple[bool, Optional[str], Optional[discord.Message]]: 
            - success (bool): True se il recupero è riuscito
            - content (str): Il contenuto del messaggio o il messaggio di errore
            - reference_message (discord.Message): Il messaggio di riferimento se trovato
    """
    if not ctx.message.reference:
        return True, None, None
        
    try:
        reference_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        logger.debug(f"Messaggio di riferimento trovato: {reference_message.id}")
        
        # Se il messaggio ha allegati, controlla se c'è un file .txt
        if reference_message.attachments:
            for attachment in reference_message.attachments:
                if attachment.filename.lower().endswith('.txt'):
                    content = await attachment.read()
                    content = content.decode('utf-8')
                    return True, clean_content(content), reference_message
        
        # Se non ci sono allegati .txt, usa il contenuto del messaggio
        content = clean_content(reference_message.content)
        return True, content, reference_message
        
    except discord.NotFound:
        logger.error("Messaggio di riferimento non trovato")
        return False, messages["draft_reference_not_found"], None
    except discord.Forbidden:
        logger.error("Permessi insufficienti per accedere al messaggio di riferimento")
        return False, messages["draft_reference_forbidden"], None
    except Exception as e:
        logger.error(f"Errore durante il recupero del messaggio di riferimento: {str(e)}", exc_info=True)
        return False, f"❌ Errore durante il recupero del messaggio di riferimento: {str(e)}", None

async def extract_command_argument(ctx):
    """
    Estrae l'argomento del comando dal messaggio o dall'allegato.
    
    Args:
        ctx: Il contesto del comando Discord
        
    Returns:
        tuple: (success, argument)
            - success (bool): True se l'estrazione è riuscita
            - argument (str): L'argomento estratto o il messaggio di errore
    """
    try:
        # Prima controlla se c'è un messaggio di riferimento
        ref_success, ref_content, ref_message = await get_reference_content(ctx)
        if not ref_success:
            return False, ref_content
        if ref_content:
            return True, ref_content
            
        # Se non c'è un messaggio di riferimento o non ha contenuto, controlla il messaggio corrente
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.endswith('.txt'):
                    # Scarica il contenuto del file
                    content = await attachment.read()
                    content = content.decode('utf-8')
                    
                    # Pulisci il contenuto
                    content = clean_content(content)
                    
                    logger.debug(f"Contenuto estratto da file .txt ({len(content)} caratteri)")
                    return True, content
                    
            return False, messages["draft_invalid_attachment"]
            
        # Se non ci sono allegati, usa il contenuto del messaggio
        content = ctx.message.content.split(' ', 1)
        if len(content) > 1:
            return True, clean_content(content[1])
        else:
            return False, messages["draft_missing_input"]
            
    except Exception as e:
        logger.error(f"Errore durante l'estrazione dell'argomento: {str(e)}")
        return False, f"❌ Errore durante l'estrazione dell'argomento: {str(e)}"

def format_error_message(error: str) -> str:
    """
    Formatta un messaggio di errore in modo consistente.
    
    Args:
        error: Il messaggio di errore
        
    Returns:
        str: Il messaggio formattato
    """
    return f"❌ {error}" 