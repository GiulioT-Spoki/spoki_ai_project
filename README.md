# Spoki Doc Bot

Un bot Discord per la gestione e l'organizzazione della documentazione.

## Requisiti

- Python 3.8 o superiore
- pip (gestore pacchetti Python)

## Installazione

1. Clona il repository:
```bash
git clone https://github.com/tuousername/Spoki-Doc-Bot.git
cd Spoki-Doc-Bot
```

2. Crea un ambiente virtuale e attivalo:
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

3. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

4. Crea un file `.env` nella root del progetto con le seguenti variabili:
```
DISCORD_TOKEN=il_tuo_token_discord
DISCORD_PREFIX=il_tuo_prefisso
OPENAI_API_KEY=la_tua_api_key_openai
```

5. Configura il file `config/config.json` con le impostazioni appropriate.

## Avvio

Per avviare il bot:
```bash
python bot.py
```

## Funzionalità

- Gestione documentazione
- Sistema di draft
- Gestione topic
- Generazione articoli con AI
- Ricerca articoli correlati
- Sistema di logging avanzato

## Note sui comandi Discord

I comandi che accettano argomenti funzionano sia in formato:
- `!comando <argomento>`
- `<argomento> !comando`

**Attenzione:** Questo vale solo per i comandi esplicitamente elencati nell'evento `on_message` in `bot.py` (es: `!topic`, `!draft`).
Per aggiungere altri comandi a questa funzionalità, aggiorna la lista in `bot.py`.

## Limiti dei Comandi

I comandi del bot hanno limiti di lunghezza per gli argomenti che vengono applicati al momento dell'invocazione su Discord. Questi limiti sono definiti nel file `config/config.json` nella sezione `commands`:

```json
"commands": {
    "topic": {
        "min_length": 3,
        "max_length": 100,
        "description": "Comando per cercare documenti su un argomento specifico"
    },
    "draft": {
        "min_length": 5,
        "max_length": 200,
        "description": "Comando per generare una bozza di articolo"
    }
}
```

### Spiegazione dei Limiti

- **!topic**: 
  - Min: 3 caratteri
  - Max: 100 caratteri
  - Questo limite è allineato con il limite dei titoli dei thread di Discord
  - L'argomento viene usato come titolo del thread di ricerca

- **!draft**:
  - Min: 5 caratteri
  - Max: 200 caratteri
  - L'argomento serve come "seed" per la generazione dell'articolo
  - Il contenuto finale dell'articolo può essere molto più lungo

### Come Modificare i Limiti

Per modificare i limiti di un comando:

1. Apri il file `config/config.json`
2. Trova la sezione `commands`
3. Modifica i valori di `min_length` e `max_length` per il comando desiderato
4. Salva il file

**Nota**: Modificare questi limiti potrebbe influire sull'usabilità del bot. Si consiglia di:
- Mantenere il limite di `topic` allineato con `thread_title_limit` di Discord (100 caratteri)
- Considerare che argomenti troppo lunghi potrebbero essere difficili da gestire nell'interfaccia Discord

## Supporto per File .txt nel Comando !draft

Il comando `!draft` supporta l'uso di file .txt come input. Questo permette di:
- Inviare contenuti più lunghi rispetto al limite standard dei messaggi Discord
- Mantenere la formattazione originale del testo
- Gestire documenti più complessi

### Come Usare i File .txt

1. Prepara un file .txt con il contenuto desiderato
2. Invia il file come allegato in un messaggio che contiene il comando `!draft`
3. Il bot leggerà automaticamente il contenuto del file e lo userà come argomento per il comando

**Note Importanti**:
- Solo i file .txt sono supportati
- Il contenuto del file non è soggetto ai limiti di lunghezza standard del comando
- La formattazione del testo nel file viene preservata
- Il nome del file non viene utilizzato come argomento, solo il suo contenuto

### Esempio di Utilizzo

```
!draft [allegato: documento.txt]
```

Il contenuto di `documento.txt` verrà utilizzato come argomento per la generazione della bozza.

## Configurazione del Modello AI

Il bot utilizza ChatGPT per generare gli articoli. Le impostazioni del modello sono configurabili nel file `config/config.json` nella sezione `ai`:

```json
"ai": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens_ratio": 0.7,
    "token_limits": {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4-32k": 32768
    }
}
```

### Spiegazione delle Impostazioni

- **model**: Il modello di ChatGPT da utilizzare
  - `gpt-3.5-turbo`: Più veloce ed economico (default)
  - `gpt-4`: Più accurato ma più costoso
  - `gpt-4-32k`: Versione con contesto più ampio

- **temperature**: Controlla la creatività del modello (0.0 - 1.0)
  - Valori più bassi = risposte più deterministiche
  - Valori più alti = risposte più creative
  - Default: 0.7 (buon equilibrio)

- **max_tokens_ratio**: Percentuale massima di tokens da usare per il prompt
  - Default: 0.7 (70% del limite del modello)
  - Il resto è riservato per la risposta

- **token_limits**: Limiti di tokens per ogni modello
  - `gpt-3.5-turbo`: 4096 tokens
  - `gpt-4`: 8192 tokens
  - `gpt-4-32k`: 32768 tokens

### Gestione dei Token e Margine di Sicurezza

Il bot implementa un sistema di gestione dei token con margine di sicurezza per evitare errori di superamento del limite del modello:

1. **Calcolo dei Token**:
   - Il prompt viene stimato in token (≈ 4 caratteri = 1 token)
   - Il limite del modello viene letto dalla configurazione
   - I token per la risposta vengono calcolati come: `(model_limit - estimated_tokens) * 0.9`

2. **Margine di Sicurezza**:
   - Il 10% dei token disponibili viene riservato come margine di sicurezza
   - Se il prompt usa più del 90% dei token disponibili, viene rifiutato
   - Questo previene errori di "context_length_exceeded"

3. **Esempio Pratico**:
   - Con GPT-4 (8192 token):
     - Prompt: 2100 token
     - Token disponibili: 8192 - 2100 = 6092
     - Token per risposta: 6092 * 0.9 = 5483
     - Margine di sicurezza: 6092 * 0.1 = 609

4. **Logging**:
   - Il bot logga i dettagli del calcolo dei token
   - Esempio: `Token stimati: 2100, Limite modello: 8192, Token per risposta: 5483`

### Limiti dei File .txt

Quando si usa un file .txt con il comando `!draft`, il sistema:
1. Stima il numero di tokens del contenuto (≈ 4 caratteri = 1 token)
2. Verifica che non superi il limite configurato

## Sistema di Articoli Correlati

Il bot implementa un sistema automatico di ricerca e aggiunta di articoli correlati agli articoli generati. Questo sistema:

1. **Estrazione Keywords**:
   - Estrae automaticamente 3-5 keywords dal blocco SEO dell'articolo generato
   - Le keywords vengono estratte dal blocco HTML nascosto alla fine dell'articolo

2. **Ricerca Articoli**:
   - Per ogni keyword, cerca articoli correlati nel database
   - Evita duplicati tra i risultati
   - Limita i risultati a 5 articoli correlati

3. **Formattazione**:
   - Crea una sezione "Articoli correlati" con header `<h2>`
   - Formatta gli articoli come lista puntata con link
   - Inserisce la sezione prima del blocco SEO

4. **Feedback Utente**:
   - Informa l'utente del numero di keywords estratte
   - Notifica il numero di articoli correlati trovati
   - Fornisce feedback in caso di nessun articolo correlato trovato

### Esempio di Output

```html
<!-- wp:heading -->
<h2>Articoli correlati</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
<li><a href="https://support.spoki.it/articolo1">Titolo Articolo 1</a></li>
<li><a href="https://support.spoki.it/articolo2">Titolo Articolo 2</a></li>
...
</ul>
<!-- /wp:list -->
```

## Changelog

### v1.1.0 (2024-05-08)
- Aggiunto sistema di articoli correlati automatico
- Migliorato il prompt per la generazione di articoli originali
- Aggiunto feedback in tempo reale durante la generazione
- Ottimizzato il sistema di logging

### v1.0.0 (2024-05-01)
- Rilascio iniziale
- Implementazione comandi base (!draft, !topic)
- Supporto per file .txt
- Integrazione con ChatGPT
- Sistema di logging

## Licenza

Questo progetto è sotto licenza MIT.

## Personalizzazione del comando !status e dei messaggi embed

Il comando `!status` mostra lo stato attuale del bot tramite un messaggio **embed** su Discord, con campi separati e link cliccabili.

### Come personalizzare i nomi dei campi dell'embed

I nomi dei campi visualizzati nell'embed (ad esempio "Articoli correlati", "YouTube", "Dominio WordPress") sono configurabili direttamente dal file:

```
config/messages.json
```

Le chiavi da modificare sono:

- `status_title`: Titolo dell'embed
- `status_field_articles`: Nome del campo per gli articoli correlati
- `status_field_videos`: Nome del campo per i video correlati
- `status_field_youtube`: Nome del campo per il canale YouTube
- `status_field_wordpress`: Nome del campo per il dominio WordPress

Esempio:
```json
"status_title": "📊 Stato attuale del bot",
"status_field_articles": "📰 Articoli correlati",
"status_field_videos": "🎥 Video correlati",
"status_field_youtube": "▶️ YouTube",
"status_field_wordpress": "🌐 Dominio WordPress"
```

### Come funziona la visualizzazione del dominio

Il campo "Dominio WordPress" mostra solo il nome del dominio (senza https://) come testo cliccabile, mentre il link porta all'URL completo.

### Come aggiornare i testi

Per cambiare le etichette o le emoji, modifica semplicemente i valori corrispondenti in `messages.json` e riavvia il bot (o usa un comando di reload se disponibile).

---