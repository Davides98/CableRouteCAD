# CableRouteCAD

## Documentazione e Manuale Utente

## Introduzione

**CableRouteCAD** è un software dedicato alla progettazione, gestione e instradamento automatico di cavi elettrici e di comunicazione su planimetrie CAD.

L’obiettivo principale del programma è automatizzare il calcolo dei percorsi dei cavi (*routing*), garantendo che ogni collegamento segua un tragitto fisicamente valido attraverso le infrastrutture disponibili (passerelle, tubazioni, cavedi), nel rispetto dei vincoli di segregazione dei servizi (ad esempio separazione tra cavi di potenza e dati) e della continuità della rete.

CableRouteCAD è pensato per ridurre drasticamente i tempi di progettazione, minimizzare gli errori manuali e fornire una visione chiara e verificabile dello stato di saturazione delle infrastrutture.

---

## Flusso di Lavoro Tipico

1. **Creazione di un Nuovo Progetto**  
   L’utente avvia un nuovo progetto importando una planimetria in formato **DXF** e un file **CSV**, oppure partendo da un progetto vuoto.

2. **Definizione delle Passerelle** *(Work in Progress)*  
   Selezionando i segmenti disegnati, l’utente assegna le caratteristiche delle passerelle (ad esempio: *Canale 300x100 – Power*).  
   Su uno stesso segmento possono coesistere più passerelle, consentendo la separazione logica dei servizi (es. Forza Motrice e Segnali).

3. **Posizionamento dei Quadri e delle Utenze**  
   Vengono definite le posizioni dei quadri elettrici, degli armadi o delle utenze sulla rete. Questi elementi rappresentano i punti di origine (*FROM*) e destinazione (*TO*) dei cavi.

4. **Calcolo Automatico dei Percorsi**  
   Con un singolo comando, il software elabora l’instradamento di tutti i cavi presenti nella lista.

5. **Analisi e Verifica**

   * Visualizzazione grafica dei percorsi calcolati.
   * Consultazione della **Heatmap**, che evidenzia i segmenti in base al carico o al numero di cavi.
   * Analisi della lista errori per individuare cavi non instradabili o configurazioni incomplete.

---

## Funzionalità Principali

### 1. Interfaccia Grafica (GUI)

* **Canvas Interattivo**  
  Navigazione fluida (Zoom e Pan) anche su file DXF complessi e di grandi dimensioni.

* **Gestione dei Layer**  
  Possibilità di mostrare o nascondere elementi come griglia, nodi del grafo, etichette testuali e quote dimensionali.

* **Dock Mobili**  
  Pannelli dedicati a Connessioni, Lista Quadri, Proprietà ed Errori, liberamente spostabili, ancorabili o chiudibili.

---

### 2. Motore di Routing

Il cuore del software è un motore di calcolo basato su un algoritmo di ricerca su grafo **A***, opportunamente adattato al contesto impiantistico.

* **Segregazione dei Servizi**  
  Ogni cavo viene instradato esclusivamente su passerelle compatibili con il servizio definito (es. *Power*, *Data*, *Misti*).  
  Se un percorso fisico esiste ma non rispetta le regole di segregazione, il cavo non viene instradato.

* **Percorso Minimo**  
  Tra tutte le alternative valide, il sistema seleziona sempre il percorso con lunghezza complessiva minore.

* **Verifica della Continuità Fisica**  
  Il motore rileva automaticamente se i quadri di partenza e arrivo non risultano fisicamente collegati dalla rete disegnata.

---

### 3. Gestione dei Dati

* **Formato CSV Flessibile**  
  Il software riconosce colonne come `FROM`, `TO`, `Tipo`, `Formazione`, `Diametro`, gestendo anche alias comuni (ad esempio `Cable Type`, `Service`).

* **Formato di Progetto (.cvp)**  
  L’intero stato del progetto, inclusa la planimetria DXF di sfondo, viene salvato in un unico file compresso, facilmente archiviabile e condivisibile.

---

### 4. Visualizzazione Avanzata

* **Etichette Dinamiche**  
  Ogni segmento può visualizzare in tempo reale le passerelle presenti e le relative caratteristiche.

* **Quote Dimensionali**  
  La lunghezza dei segmenti è mostrata direttamente sul disegno, facilitando il controllo metrico.

* **Heatmap di Carico**  
  Rappresentazione cromatica (dal verde al rosso) per individuare immediatamente tratte critiche.

---

### 5. Controlli di Integrità e Validazione

* Rilevamento automatico di auto-connessioni (origine e destinazione coincidenti).
* Segnalazione di quadri mancanti o di nomi non corrispondenti tra disegno e lista cavi.
* Log dettagliato delle operazioni di routing, utile per analisi e troubleshooting.

---

## Requisiti di Sistema

* Sistema operativo **Windows 10 / 11**.
* Applicazione **standalone**, senza dipendenze esterne.
* Mouse con rotellina consigliato per una navigazione ottimale del canvas.
