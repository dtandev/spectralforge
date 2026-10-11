# Schemat bazy danych — SpectralForge × SpectralHub

Data: 2026-07-25
Kontekst: `docs/Plan_badawczy_SpectralForge.md`. Analiza oparta o bibliotekę
`/Users/dariusz.tanajewski/Documents/Code/spectralhub/` (`SpectralDatabase`, `Signature`,
`SpectralProfile`, `BandResampler`, `processing_tools`).

<!-- TODO: verify this — dokument roboczy; część ustaleń wymaga potwierdzenia po uzyskaniu
żywego dostępu do bazy (patrz Sekcja 3). -->

## 1. Status połączenia z bazą

Próba połączenia z żywą bazą (`SpectralDatabase.connect()` z parametrami z `secrets.json`)
**nie powiodła się** z tego środowiska:

```
psycopg2.OperationalError: connection to server at "dev-terraeye.postgres.database.azure.com"
(20.86.160.85), port 5432 failed: Operation timed out
```

Ogólny dostęp do internetu z tego środowiska działa (test do google.com: HTTP 200), ale port
5432 do hosta Azure jest niedostępny — najprawdopodobniej firewall bazy Azure wpuszcza tylko
ruch z Twojej sieci/VPN, nie z tego środowiska wykonawczego. Nie próbowałem tego obchodzić.

**Poniższe ustalenia pochodzą z analizy statycznej kodu (`spectralhub/*.py`) oraz z zapisanych
wyników rzeczywistych zapytań w `examples/spectralhub_showcase.ipynb`** (uruchomionym wcześniej
przez Ciebie) — nie z połączenia na żywo. Gdzie oznaczono `TODO: verify this`, wymaga to
potwierdzenia żywym zapytaniem.

Przygotowałem gotowy skrypt inspekcyjny (tylko odczyt, żadnych modyfikacji) w
`/private/tmp/.../scratchpad/inspect_db.py` z tej sesji — jeśli uruchomisz go ze swojej
maszyny (ma dostęp do `secrets.json` i pełnego `spectralhub`), zwróci listę tabel, liczności
wierszy, listę `spectral_profiles` i schemat kolumn każdej tabeli `*_samples`/`*_spectra`.
Chętnie dopracuję ten schemat, gdy podeślesz wynik, albo jeśli wolisz, mogę spróbować
ponownie, gdyby firewall bazy dopuszczał to środowisko.

## 2. Co już istnieje w SpectralHub (nie duplikować)

### 2.1 Tabele (z realnego stanu bazy, wg notatnika)

| Tabela | Zawartość |
|---|---|
| `samples` / `spectra` | Domyślna biblioteka — **Ecostress** (baza nazywa się `ecostress-lib`; potwierdzone w notatniku: *"Domyślnie wszystkie operacje są wykonywane na bibliotece Ecostress"*) |
| `splib07b_samples` / `splib07b_spectra` | Biblioteka USGS (splib07b), zaimportowana przez `add_spectral_signatures_from_html()` z eksportu HTML |
| `Geometric-medians-USGS_samples` / `_spectra` | Prekomputowane mediany geometryczne widm per mineral — koncepcyjnie to samo co referencyjny embedding `z_c` z artykułu (eq. 17), tylko na poziomie surowych widm, nie embeddingów sieci |
| `mineral_mixtures_chile_2023_samples` / `_spectra` | **Realny zbiór zmieszanych pikseli/próbek** — potencjalny ground truth do Eksperymentu 7 (walidacja unmixing) z planu badawczego. `TODO: verify this` — trzeba sprawdzić, czy zawiera jawne udziały (abundance), czy tylko widma i opis tekstowy |
| `dt_samples` / `dt_spectra` | Prawdopodobnie osobista/testowa przestrzeń robocza |
| `spectral_profiles` | Definicje sensorów: centers, bandwidths, stdevs, jednostki. Potwierdzone providery z kodu/notatnika: Sentinel-2, ASTER, ASTER_SWIR (custom), PlanetScope, PRISMA, EnMAP, EMIT, EMIT_CUT, ASTER_TIR, WorldView-3 |

### 2.2 Schemat kolumn (z `database.py`, potwierdzony)

```sql
-- Wzorzec dla KAŻDEGO db_alias (w tym domyślnego bez prefiksu):
CREATE TABLE {alias}_samples (
    sampleid SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    class TEXT,
    subclass TEXT,
    particlesize TEXT,          -- wolny tekst, NIE numeryczne — patrz Sekcja 4.3
    samplenum TEXT,
    owner TEXT,
    origin TEXT,
    phase TEXT,
    description TEXT
);

CREATE TABLE {alias}_spectra (
    spectrumid SERIAL PRIMARY KEY,
    sampleid INTEGER REFERENCES {alias}_samples(sampleid),
    sensorcalibrationid INTEGER,
    instrument TEXT,
    environment TEXT,
    measurement TEXT,
    xunit TEXT,
    yunit TEXT,
    minwavelength REAL,
    maxwavelength REAL,
    numvalues INTEGER,
    xdata BYTEA NOT NULL,        -- float32 array, zakodowany ręcznie (convert_float_array_to_bytea)
    ydata BYTEA NOT NULL,
    location geometry(Point, 4326)
);

CREATE TABLE spectral_profiles (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    centers FLOAT8[],
    bandwidths FLOAT8[],
    centers_stdevs FLOAT8[],
    bandwidth_stdevs FLOAT8[],
    band_quantity VARCHAR(50),
    center_units VARCHAR(50)
);
```

### 2.3 Narzędzia przetwarzania (już zaimplementowane, do ponownego użycia)

- **`resampler.BandResampler`** — resampling między siatkami pasm z konwersją jednostek;
  zakłada gaussowską funkcję odpowiedzi pasma docelowego i całkuje nakładanie się pasm
  źródłowych (funkcja błędu, `normal_integral`). To w praktyce już jest bliskie temu, co
  planowaliśmy jako operator **B3** (4.1.3, konwolucja ILS) — nie trzeba budować od zera,
  wystarczy sprawdzić, czy założenie "gaussowski kształt pasma docelowego + źródło płaskie
  na swoim FWHM" jest wystarczająco bliskie realnemu ILS EMIT, czy potrzebujemy dokładniejszej
  wersji.
- **`processing_tools.continuum_removing()`** — usuwanie kontinuum metodą otoczki wypukłej
  (ConvexHull). To dokładnie ta sama metoda, która w artykule ESWA generuje artefakt z Rys. 6
  (odbicie >1.3 po zastosowaniu do sztucznie zmieszanego widma) — przy budowie guardraila
  (B8, 4.1.8) warto to świadomie testować na wyjściu tej właśnie funkcji, a nie zakładać, że
  jest bezpieczna.
- **`processing_tools.band_depth_calculation()` / `calculate_absorption_center()`** —
  parametryzacja cech diagnostycznych (głębokość pasma, centrum absorpcji) w duchu Clark et
  al. (1990) — dokładnie to, co rozważaliśmy jako "metodę wykraczającą poza artykuł"
  (parametryzacja cech diagnostycznych). Już istnieje, gotowe do użycia.
- **`processing_tools.calculate_SAM()` / `calculate_sff()`** — Spectral Angle Mapper i
  Spectral Feature Fitting — przydatne przy walidacji podobieństwa par pozytywnych/negatywnych
  w kontekście metric-learning z artykułu.
- **`SpectralImage`** (rasterio-based) — `get_spectral_curve(lat, lon)` do wyciągania
  realnego widma z obrazu satelitarnego (np. sceny EMIT/AVIRIS Cuprite) — przydatne przy
  Eksperymencie 6 (transfer na teren złożony topograficznie) i przy budowie guardraila
  względem realnych danych.

**Wniosek:** SpectralForge nie powinien duplikować DB-access, resamplingu, continuum removal
ani metryk podobieństwa — powinien **zależeć od SpectralHub** (import biblioteki) i budować
na tym warstwę: (a) fizycznie umotywowane operatory augmentacji B1-B8 z planu badawczego,
(b) rozszerzenia z Sekcji 4.3 (unmixing, tło niemineralne, serie ziarna, N-składnikowe
mieszanki), (c) **proweniencję** wygenerowanych danych — czego SpectralHub obecnie w ogóle
nie ma (widmo dodane przez `add_signature()` nie zapisuje skąd pochodzi ani jakimi
parametrami augmentacji powstało).

## 3. Czego brakuje — proponowany schemat SpectralForge

Nowy, osobny schemat Postgres (`spectralforge`), logicznie oddzielony od `public` (własność
SpectralHub), żeby nie ryzykować kolizji z istniejącymi tabelami ani nie wymagać migracji
istniejących danych. SpectralForge **czyta** z tabel SpectralHub (przez `SpectralDatabase`/
`Signature`), ale **zapisuje** wygenerowane dane do swojego schematu.

```sql
CREATE SCHEMA IF NOT EXISTS spectralforge;

-- Rejestr "uruchomień" operatora augmentacji — jeden wiersz na zestaw parametrów
CREATE TABLE spectralforge.operator_runs (
    run_id            SERIAL PRIMARY KEY,
    operator_code     TEXT NOT NULL,        -- 'B1'..'B8', 'unmixing', 'grain_series', 'n_endmember', ...
    operator_version  TEXT,                 -- wersja pakietu/commit — dla odtwarzalności
    parameters        JSONB NOT NULL,       -- np. {"theta_i": 12.4, "theta_ref": 0} — elastyczne, różne na operator
    dataset_batch     TEXT,                 -- nazwa eksperymentu/wydania, np. 'ablation_B1_v1'
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    guardrail_passed  BOOLEAN,
    guardrail_notes   TEXT
);

-- Same wygenerowane/syntetyczne widma
CREATE TABLE spectralforge.generated_spectra (
    spectrum_id       SERIAL PRIMARY KEY,
    run_id            INTEGER NOT NULL REFERENCES spectralforge.operator_runs(run_id),
    mineral_class     TEXT,                 -- zdenormalizowana etykieta, wygodna do ML
    xunit             TEXT NOT NULL,
    yunit             TEXT NOT NULL,
    band_centers      FLOAT8[] NOT NULL,    -- natywna tablica Postgres — bez ręcznego BYTEA (jak w spectral_profiles.centers)
    reflectance       FLOAT8[] NOT NULL,
    minwavelength     REAL,
    maxwavelength     REAL,
    numvalues         INTEGER,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Powiązanie N:M — z jakich widm źródłowych (i z jaką wagą/udziałem) powstało widmo wygenerowane
-- weight=1.0 dla operatorów jednospektralnych (B1-B5); wiele wierszy sumujących się do 1 dla mieszanek (B6/B7/N-endmember)
CREATE TABLE spectralforge.generation_inputs (
    generated_spectrum_id  INTEGER NOT NULL REFERENCES spectralforge.generated_spectra(spectrum_id),
    source_db_alias        TEXT NOT NULL DEFAULT '',  -- np. 'splib07b'; '' = domyślne tabele ecostress-lib
                                                       -- (pusty string, nie NULL — NULL nie może być częścią PRIMARY KEY)
    source_spectrum_id     INTEGER NOT NULL,-- odpowiada {alias}_spectra.spectrumid w schemacie SpectralHub
    weight                 FLOAT8 NOT NULL DEFAULT 1.0,  -- udział (abundance) dla mieszanek
    grain_size_um           FLOAT8,          -- dla serii wielkości ziarna via Hapke (4.3.3)
    PRIMARY KEY (generated_spectrum_id, source_db_alias, source_spectrum_id)
);
```

### Uzasadnienie decyzji projektowych

- **`parameters JSONB`, nie kolumna-na-parametr.** Każdy operator (B1-B8, unmixing, grain-size,
  N-endmember) ma inny zestaw parametrów — sztywny schemat kolumnowy wymagałby albo bardzo
  szerokiej tabeli z mnóstwem NULL-i, albo osobnej tabeli na operator. JSONB trzyma to
  elastycznie, kosztem słabszej walidacji na poziomie bazy (do egzekwowania w warstwie
  aplikacji SpectralForge, np. przez schemat Pydantic per operator).
- **`FLOAT8[]` zamiast `BYTEA`.** SpectralHub koduje `xdata`/`ydata` ręcznie do BYTEA
  (`convert_float_array_to_bytea`/`convert_bytea_to_float_array`) — to działa, ale wymaga
  ręcznej (de)serializacji przy każdym odczycie/zapisie. `spectral_profiles.centers` w tej
  samej bazie już używa natywnego `FLOAT8[]` — proponuję konsekwentnie iść tą drogą dla
  nowych tabel SpectralForge, prościej i czytelniej w SQL (np. `unnest()`, `array_length()`).
- **Brak twardego FK do tabel SpectralHub.** `source_spectrum_id`/`source_db_alias` wskazują
  na wiersze w dynamicznie nazwanych tabelach SpectralHub (`{alias}_spectra`), których nazwa
  zależy od `db_alias` — Postgres nie pozwala na FK do tabeli wybieranej w runtime. Integralność
  między `spectralforge.generation_inputs` a źródłowymi widmami trzeba więc pilnować na
  poziomie aplikacji (np. sprawdzić przy zapisie, czy `source_spectrum_id` istnieje w
  `{source_db_alias}_spectra`). To świadomy kompromis, nie przeoczenie.
- **`dataset_batch` jako zwykły TEXT, nie osobna tabela.** Prostsze na start; jeśli w miarę
  rozwoju eksperymentów z Sekcji 5 planu badawczego (ablacje, warianty) potrzeba będzie
  bogatszych metadanych batcha (kto uruchomił, jaki commit kodu, jaki wynik F1), łatwo
  dodać `spectralforge.dataset_batches` jako osobną tabelę z FK z `operator_runs.dataset_batch`
  bez zrywania istniejącego schematu.

## 4. Otwarte pytania / do potwierdzenia po uzyskaniu dostępu do bazy

1. **Dostęp sieciowy.** ✅ Rozwiązane częściowo — zamiast doraźnego skryptu w scratchpadzie,
   `scripts/inspect_live_db_schema.py` jest teraz częścią repo (`just db-inspect`), czyta
   dane logowania z `.env` (nie z `secrets.json` — sekrety SpectralHub nigdy nie trafiają
   do tego repo), i zapisuje pełny wynik do `db/schema_snapshot.json`. Uruchom go ze swojej
   maszyny/VPN, kiedy będziesz gotów — potwierdzenie prób połączenia z tego środowiska
   (nawet z włączonym VPN po Twojej stronie) kończyło się timeoutem, więc zakładam pracę
   offline względem żywej bazy do czasu, aż podeślesz `db/schema_snapshot.json`.
2. **`mineral_mixtures_chile_2023`** — czy tabela zawiera jawne udziały mineralne (np. w
   `description` albo osobnych kolumnach), czy tylko widma i metadane tekstowe? To rozstrzyga,
   czy nadaje się bezpośrednio jako ground truth do Eksperymentu 7, czy trzeba dociągnąć
   udziały z innego źródła (raport terenowy, XRD).
3. **Realna liczba widm per mineral w `splib07b`** (i per klasa/podklasa) — rozstrzyga
   otwarte pytanie z planu badawczego o sensowności ścieżki generatywnej (Eksperyment 10).
4. **`particlesize` jako TEXT** w `samples` — dla serii wielkości ziarna (4.3.3, `grain_size_um`
   w `generation_inputs`) będziemy potrzebować numerycznej wartości. Czy wolisz, żebym:
   (a) parsował istniejące opisy tekstowe USGS (np. "&lt;45 μm") przy imporcie do
   `generation_inputs.grain_size_um`, zostawiając `samples.particlesize` w SpectralHub bez
   zmian, czy (b) proponował SpectralHub dodanie numerycznej kolumny — to już ingerencja
   w cudzy (choć Twój) projekt, więc wolę zapytać niż zakładać.
5. **Właściciel schematu `spectralforge`.** Czy ma to być ten sam serwer/baza Azure (`dev-terraeye`),
   nowy schemat obok `public`, czy wolisz osobną instancję/bazę dla SpectralForge, żeby
   eksperymentalne dane augmentacji nie mieszały się fizycznie z produkcyjną biblioteką
   referencyjną SpectralHub?
