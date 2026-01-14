# CableRouteCAD - Documentazione e Manuale

## Introduzione
**CableRouteCAD** è un software specializzato per la progettazione, la gestione e l'instradamento automatico di cavi elettrici e dati su planimetrie CAD. 

L'obiettivo principale del programma è automatizzare il calcolo dei percorsi dei cavi (Routing), garantendo che ogni cavo segua un tragitto valido attraverso le passerelle disponibili, rispettando i vincoli di segregazione (es. separazione tra cavi di potenza e dati) e continuità fisica.

## Flusso di Lavoro Tipico

1.  **Nuovo Progetto**: Si inizia importando una planimetria in formato **DXF** (o creando un progetto vuoto).
2.  **Disegno della Rete**: L'utente disegna linee sulla planimetria che rappresentano i percorsi fisici (passerelle, tubazioni, cavedi). Il software crea automaticamente un grafo di nodi interconnessi.
3.  **Definizione Passerelle**: Selezionando i segmenti disegnati, l'utente assegna le specifiche delle passerelle (es. "Canale 300x100 - Power"). È possibile avere più passerelle sullo stesso segmento (es. una per Forza Motrice, una per Segnali).
4.  **Posizionamento Quadri**: Si definiscono le posizioni dei Quadri (Switchboards) o delle utenze sulla rete. Questi sono i punti di partenza e arrivo dei cavi ('FROM' e 'TO').
5.  **Importazione Lista Cavi**: Si carica un file **CSV** contenente l'elenco dei cavi da posare.
6.  **Calcolo Percorsi**: Con un click, il software elabora tutti i collegamenti.
7.  **Analisi**: 
    *   Si visualizzano i percorsi tracciati.
    *   La **Heatmap** colora i segmenti in base al riempimento o al numero di cavi.
    *   Si verifica la lista degli errori (cavi non instradabili).
8.  **Esportazione**: Si esporta il computo metrico (Bill of Quantities) con le lunghezze totali per ogni tipo di cavo.

## Funzionalità Principali

### 1. Interfaccia Grafica (GUI)
*   **Canvas Interattivo**: Navigazione fluido (Zoom, Pan) su file DXF anche complessi.
*   **Gestione Layer**: Possibilità di nascondere/mostrare la griglia, i nodi del grafo, le etichette di testo e le quote.
*   **Dock Mobili**: Pannelli per Connessioni, Liste Quadri, Proprietà e Errori che possono essere spostati o chiusi.

### 2. Motore di Routing
Il software utilizza un algoritmo di ricerca su grafo (**A-Star**) adattato:
*   **Segregazione Servizi**: Un cavo definito come "Data" nel CSV cercherà di passare solo su passerelle o tubi abilitati per "Data" o "Misti". Se esiste un percorso fisico ma è riservato solo a "Power", il cavo non verrà instradato.
*   **Percorso Minimo**: Tra tutte le strade possibili, sceglie sempre la più breve.
*   **Verifica Continuità**: Rileva se quadri di partenza e arrivo sono fisicamente collegati.

### 3. Gestione Dati
*   **Formato CSV Flessibile**: Riconosce colonne come `FROM`, `TO`, `Tipo`, `Formazione`, `Diametro`. Gestisce alias comuni (es. `Cable Type` o `Service`).
*   **Formato Progetto (.cvp)**: Salva l'intero stato del lavoro (incluso il DXF di sfondo) in un unico file compresso, facile da condividere.

### 4. Visualizzazione Avanzata
*   **Etichette Dinamiche**: Mostra su ogni segmento quali passerelle sono presenti.
*   **Quote (Dimensioni)**: Visualizza la lunghezza dei segmenti direttamente sul disegno.
*   **Heatmap**: Visualizzazione a colori (verde -> rosso) per identificare immediatamente i colli di bottiglia o le tratte più affollate.

### 5. Controlli di Integrità
*   Rilevamento Auto-connessioni (Partenda = Arrivo).
*   Segnalazione di Quadri mancanti o nomi non corrispondenti.
*   Log dettagliato delle operazioni di routing.

## Requisiti di Sistema
*   Windows 10/11.
*   Nessuna dipendenza esterna (l'eseguibile è standalone).
*   Mouse con rotellina consigliato per lo zoom.
