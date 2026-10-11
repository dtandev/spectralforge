# Plan — SpectralForge jako generator scen hiperspektralnych (Faza 3)

Data: 2026-07-25
Punkt wyjścia: `docs/plan_wersji_2.md` (notatka autora), `docs/Podzial_na_moduly_SpectralForge.md`
(M0–M12, Faza 1–2).

<!-- TODO: verify this — dokument roboczy; wymaga potwierdzenia priorytetów i zakresu przez autora. -->

## 1. Wizja

Nie generator obrazów RGB terenu (jak popularne proceduralne/GAN-owe generatory tekstur
satelitarnych), tylko generator **pełnych scen hiperspektralnych** — kostek widmowych, nie
obrazów RGB — gdzie:

1. Istnieje spójny przestrzennie układ semantyczny ("co jest gdzie": zieleń, konkretny
   minerał, cień, woda, teren goły...).
2. Każdy piksel w obrębie tej samej klasy dostaje sygnaturę spektralną z **spójnej rodziny**
   (produkowanej przez operatory B1–B8 z Fazy 1), nie losowaną niezależnie z całego zakresu
   zmienności klasy — sąsiadujące piksele tej samej klasy mają być spektralnie spójne.

To bezpośrednio adresuje problem, na który skarży się sam artykuł ESWA: brak dostępnych,
oznaczonych danych hiperspektralnych do treningu. Taki generator produkowałby scenę razem
z pełną, pikselową prawdą naziemną (mapa klas/udziałów) — praktycznie niedostępną inaczej.

## 2. Architektura — kluczowe elementy

1. **Generator układu semantycznego** — mapa "co jest gdzie", spójna przestrzennie (płaty,
   nie szum sól-i-pieprz). Rekomendacja: łączyć realne mapy (Swayze/Cuprite,
   `mineral_mixtures_chile_2023` — już mamy dostęp) jako szablon warstwy mineralnej z
   wygenerowaną warstwą tła (patrz Sekcja 4, TerraMind).
2. **Pole udziałów subpikselowych** — miękkie udziały na granicach klas zamiast twardej mapy
   klas. Podłącza się bezpośrednio do M7 (tło niemineralne) i M8 (mieszanki N-składnikowe)
   z Fazy 1/2.
3. **Przypisanie sygnatur ze spójnością przestrzenną** — sedno techniczne: zamiast losować
   parametry augmentacji (kąt oświetlenia, wielkość ziarna, szum) niezależnie na piksel,
   użyć przestrzennie skorelowanego pola losowego (Gaussian random field z parametrem
   "długość korelacji") do wygładzenia parametrów w przestrzeni. Rozszerza M3 i M5 o warstwę
   przestrzenną zamiast budować coś od zera.
4. **Zastosowanie operatorów per-piksel** — B1 (oświetlenie) korzysta z przestrzennie
   zmiennego kąta padania wyliczonego z prawdziwego/syntetycznego DEM, zamiast globalnego
   skalara; B6/B7 (mieszanie) korzysta z pola udziałów z pkt 2; B2/B3/B5 (szum/resampling/
   maskowanie atmosferyczne) aplikowane na końcu, jednolicie wg profilu docelowego sensora.
5. **Render/output** — kostka widmowa jako GeoTIFF (rasterio, zgodnie z `SpectralImage` z
   SpectralHub — wynik od razu ładuje się istniejącym narzędziem), plus mapa klas/udziałów
   jako prawda naziemna zapisana obok.
6. **Walidacja realizmu** — porównanie statystyk SAM syntetycznej sceny względem prawdziwych
   scen EMIT/AVIRIS (przez `SpectralImage.get_spectral_curve`); QA wizualne przez quicklook RGB.

## 3. Krajobraz istniejących narzędzi (research 2026-07-25)

### 3.1 Symulatory fizyczne (rekomendowane jako baza/inspiracja)

| Narzędzie | Status | Dlaczego istotne |
|---|---|---|
| **DART** (CESBIO) | Dojrzały (od 1992), darmowy dla nauki, zamknięte źródło | 3D radiative transfer, symuluje pełne obrazy teledetekcyjne scen z topografią i atmosferą, dowolny kierunek Słońca/sensora — dokładnie "spójne scenariusze" fizycznie, nie losowo per piksel |
| **HySIMU** | Open-source, **Python**, opublikowany 2026-03-20 | Modularny toolkit: generator kostki prawdy naziemnej, kalkulator geometrii oświetlenia z terenu, wbudowane RTM atmosfery, resampling przestrzenny. Najbliższy gotowy szkielet dla naszej Fazy 3 — do realnej oceny jako zależność zamiast budowy własnego symulatora DEM+oświetlenie+atmosfera |
| **PROSAIL** (+ `jgomezdans/prosail`) | Dojrzały, gotowe bindingi Python | Model liścia (PROSPECT) + korony (SAIL) — fizycznie rozwiązuje "zieleń = spójna rodzina sygnatur" dla roślinności konkretnie. Naturalny kandydat do M7 zamiast generycznej biblioteki widm roślinności |
| **DIRSIG** (RIT) | Złoty standard branżowy, zamknięte źródło celowo (ryzyko rozjazdu wersji), dostępny komercyjnie via Rendered.ai | Punkt odniesienia jakościowego, nie zależność |

### 3.2 Modele generatywne ML (obrazy satelitarne ogólnie)

**DiffusionSat**, hiperspektralne prace generatywne (SpectralDiff, HSI-Gene 2026,
"Unmixing Guided Diffusion Model") — cytat wprost z bieżącej ewaluacji DiffusionSat:
*"visually convincing but not yet physically reliable"*. To ten sam problem, przed którym
uciekamy w naszych własnych operatorach (A3/A6 z artykułu ESWA). **Rekomendacja: nie
budować silnika treści spektralnej na tych modelach.** Warte obserwacji/cytowania jako
related work, nie jako fundament.

## 4. TerraMind — szczegółowa ocena do warstwy semantycznej

**Dostępność:** Apache 2.0, open-weights na HuggingFace
(`ibm-esa-geospatial/TerraMind-1.0-{tiny,small,base,large}`), kod na GitHub (`IBM/terramind`).
Wytrenowany na TerraMesh: Sentinel-1 GRD, Sentinel-2, DEM, mapy LULC (klasy ESRI/DynamicWorld),
NDVI, współrzędne, opisy tekstowe.

**Co się da wykorzystać:** tryb "any-to-any" generuje zero-shot mapę LULC **i jednocześnie
DEM** z obrazu Sentinel-2 realnego regionu (~80% SOTA w zero-shot dla LULC). To rozwiązuje
od razu dwie rzeczy naraz:
- Warstwę tła niemineralnego (M7) — spójna przestrzennie mapa woda/roślinność/zabudowa/
  teren goły.
- Warstwę topografii pod model kosinusowy oświetlenia (B1, Sekcja 2 pkt 4) — DEM generowany
  w tym samym kroku, spójny z LULC.

**Czego się NIE da:** TerraMind nigdy nie widział map alteracji mineralnej jako modalności —
jego klasy LULC to generyczne kategorie (woda, roślinność, zabudowa, teren goły, śnieg), nie
"Jarosite"/"Alunite"/"Kaolinite". **Nie zastąpi realnych map Swayze'a z Cuprite** (już mamy
dostęp przez `mineral_mixtures_chile_2023`/GT) dla warstwy mineralnej.

**Rekomendowany podział pracy:**
1. TerraMind → LULC + DEM z realnego obrazu Sentinel-2 wybranego regionu (warstwa tła +
   topografia, spójna przestrzennie, generowana raz).
2. Klasa "teren goły/skalisty" z LULC → wypełniana realnym szablonem udziałów mineralnych
   (Swayze/Cuprite) zamiast generycznego szumu — geologicznie to się składa naturalnie,
   bo strefy alteracji hydrotermalnej fizycznie leżą w terenie gołym/skalistym.
3. Cała treść spektralna (wartości odbicia) → wyłącznie nasz pipeline B1–B8/Hapke, nigdy
   bezpośrednio z wyjścia modelu generatywnego.

**Zastrzeżenie:** ~80% SOTA w zero-shot to nie 100% — dla samej mapy LULC/DEM (warstwa
kontekstowa, nie wartości spektralne) to akceptowalne ryzyko, inaczej niż przy generatywnej
augmentacji spektralnej (M10), gdzie stawka błędu jest dużo wyższa.

## 5. Miejsce w planie rozwoju

To jest **Faza 3**, wyraźnie PO M1–M8 z `Podzial_na_moduly_SpectralForge.md`, nie równolegle.
Warstwa przestrzennej spójności ma sens tylko NAD już poprawną fizyką pojedynczego piksela —
budowanie tego przed ustabilizowaniem M1–M8 tylko przeskalowałoby te same błędy w przestrzeni.

## 6. Otwarte pytania

- Czy oceniamy HySIMU jako zależność (import biblioteki) czy tylko jako inspirację
  architektoniczną do własnej implementacji warstwy terenu/oświetlenia/atmosfery?
- Który region Sentinel-2 użyć jako wejście dla TerraMind (LULC+DEM) — Cuprite (spójność z
  istniejącymi mapami Swayze) czy inny, bardziej reprezentatywny dla docelowych zastosowań?
- Czy PROSAIL wchodzi do M7 jako pełny model fizyczny, czy na start wystarczy prostsza
  biblioteka widm roślinności z USGS/Ecostress, a PROSAIL zostaje jako rozszerzenie?
- Rozmiar modelu TerraMind (tiny/small/base/large) — kompromis dokładność vs. koszt
  obliczeniowy do ustalenia przy faktycznej implementacji.
