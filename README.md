# 📐 Programma “Costruttore pareti a blocchi”

## 🎯 Obiettivo

Questo programma simula la costruzione di una parete usando blocchi prefabbricati standard e produce una **distinta base** completa (pezzi standard + pezzi da tagliare), a partire da un **file vettoriale** caricato dall’utente (SVG o DWG).  

### In sintesi:
- Carica un file con la **vista 2D frontale** di una parete.
- Costruisce la parete con blocchi di dimensioni note.
- Genera automaticamente:
  - 📋 Distinta base blocchi standard
  - ✂️ Elenco pezzi custom (da ritagliare)
  - 🖼️ Visualizzazione della parete con blocchi posizionati
  - 📄 PDF stampabile con schema e tabella blocchi

---

## 🧑‍💻 Come funziona

### 1. Input – Disegno parete
- L’utente carica un file `.svg`, `.dxf` o `.dwg`.
- Il disegno rappresenta la **vista frontale** della parete (no 3D).
- Le aperture (porte/finestre) possono essere rappresentate come fori nel disegno.

### 2. Riconoscimento forma
- Il file viene interpretato come un **poligono geometrico** tramite librerie come `shapely` o `svgpathtools`.
- L’area utile viene divisa in **fasce orizzontali** secondo l’altezza del blocco.

### 3. Riempimento (nesting) della parete
- Ogni riga viene riempita usando **blocchi prefabbricati** secondo una logica "a mattoncino":
  - Righe pari: si inizia da sinistra con blocco pieno.
  - Righe dispari: si inizia con mezzo blocco (offset), per alternare i giunti verticali.
- Algoritmo di tipo **greedy**:
  - Si usano prima i blocchi più grandi.
  - I blocchi che non entrano perfettamente vengono **ritagliati** come custom.

### 4. Output

#### Console
```plaintext
🔨 Distinta base blocchi standard:
  • 45 × std_1.00x0.30
  • 10 × std_0.50x0.30

✂️ Pezzi custom totali: 5
  1) 1.000×0.060 m @ (0.000,3.000)
  2) 1.000×0.120 m @ (1.000,3.000)
  ...
JSON
Esporta i dati completi in un file .json:

json
Copia
Modifica
{
  "standard": {
    "std_1.00x0.30": 45,
    "std_0.50x0.30": 10
  },
  "custom": [
    {
      "width": 1.0,
      "height": 0.12,
      "x": 1.0,
      "y": 3.0,
      "coords": [[...]]
    }
  ]
}
Visualizzazione
Grafico automatico generato con matplotlib

Blocchi standard: grigi

Blocchi custom: verdi con tratteggio

Contorno parete: blu

PDF Report (work in progress)
Titolo progetto, timestamp

Schema grafico con legenda

Tabelle blocchi standard e pezzi custom

Formato A4, stampabile

🧱 Libreria blocchi standard
Tipo	Dimensioni (mm)	Note
Grande	1239×495	
Medio	826×495	
Piccolo	413×495	

⚠️ Tutti i blocchi hanno altezza costante (es. 495 mm). Larghezza variabile. I blocchi custom vengono tagliati partendo da quelli piccoli.

⚙️ Componenti tecnici
Componente	Dettagli
Input Parser	Lettura e parsing SVG (con svgpathtools). DWG supportato in fase 2.
Motore di nesting	Suddivide in fasce e applica alternanza di partenza (mattoncino)
Gestione blocchi	Libreria configurabile + calcolo automatico pezzi custom
Console Debug	Stampa quantità e dimensioni blocchi
Visualizzazione	Rendering con matplotlib
Export JSON	Output leggibile con standard + custom
Export PDF	Usare reportlab, weasyprint o pdfkit (in corso di sviluppo)

📦 Deliverable Fase 1 – Entro 1 mese
Deliverable	Stato	Note
✅ Parsing SVG	Pronto	Usa svgpathtools, supporto Polygon manuale
✅ Nesting & layout	Pronto	Inclusa logica offset alternato
✅ Visualizzazione	Pronto	matplotlib + hatch
✅ Console debug	Pronto	Lista standard + custom
✅ JSON export	Pronto	Esportazione macchina
🔜 PDF export	In corso	Impaginazione finale
🔜 Web UI	Prevista	FastAPI + interfaccia a fasi successive

🔄 Evoluzioni previste (fase 2)
Supporto a porte e finestre (cutout automatici).

Ottimizzazione layout per ridurre sprechi.

Salvataggio progetti utente (gestione versioni).

Generatore automatico disegni DXF con schema taglio.
