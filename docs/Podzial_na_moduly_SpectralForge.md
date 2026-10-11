# Podział na moduły — SpectralForge

Data: 2026-07-25
Kontekst: `docs/Plan_badawczy_SpectralForge.md`. Kolejność poniżej to kolejność budowy —
każdy kolejny moduł opiera się na tym, co już istnieje w poprzednich.

<!-- TODO: verify this — propozycja do dyskusji, nie ostateczny podział. -->

## Warstwa 0 — fundament (już częściowo zbudowany)

**M0. Dostęp do danych i trwałość** — `db/schema/*.sql`, `src/db.py`, `scripts/*` (zrobione).
Reszta modułów będzie tego używać do odczytu widm źródłowych (przez
`spectralhub.SpectralDatabase`) i zapisu wygenerowanych widm + proweniencji
(`spectralforge.operator_runs`/`generated_spectra`/`generation_inputs`).

## Warstwa 1 — narzędzia współdzielone przez wszystkie operatory

**M1. Guardrail fizyczny (B8, plan Sekcja 4.1.8).** Budowany jako drugi moduł celowo, nie
ostatni — każdy kolejny operator będzie przez niego przepuszczał wynik. Zakres: sprawdzenie
[0,1], wypukłość otoczki kontinuum (reużywa `continuum_removing` z SpectralHub), zapis
`guardrail_passed`/`guardrail_notes` do `operator_runs`. Brak zależności poza numpy/scipy.

**M2. Resampling / odpowiedź instrumentu (B3, plan Sekcja 4.1.3).** W dużej mierze
already-solved — cienki wrapper na `spectralhub.resampler.BandResampler` + pobieranie
profili z `spectral_profiles`. Szybki do zrobienia, potrzebny innym operatorom (np. B1
pracuje sensowniej na siatce docelowego sensora).

## Warstwa 2 — operatory jednospektralne (niezależne od siebie, można równolegle)

**M3. Radiometria pojedynczego widma** — B1 (oświetlenie/topografia), B2 (szum sensora),
B4 (dryft kalibracji λ), B5 (maskowanie atmosferyczne). Grupuję je razem, bo mają
identyczny kształt interfejsu (jedno widmo wejściowe → jedno wyjściowe + parametry),
więc naturalnie dzielą wspólny szkielet operatora.

## Warstwa 3 — mieszanie (rosnąca złożoność)

**M4. Mieszanie arealne/liniowe (B6, plan Sekcja 4.1.6).** Najprostszy przypadek,
fundament pod Hapke.

**M5. Mieszanie intymne Hapke + serie wielkości ziarna (B7, plan Sekcja 4.3.3).** Budowany
jako jeden moduł, bo to dosłownie ten sam mechanizm (zmiana `D_j` przy stałym `M_j` daje
serię ziarna) — nie warto sztucznie rozdzielać.

**M6. Unmixing (plan Sekcja 4.3.1).** Wymaga stabilnego mieszania (M4/M5) jako punktu
odniesienia do walidacji odzysku udziałów — stąd budowany dopiero teraz, zgodnie z planem
Sekcja 6 ("wymaga najpierw stabilnego modułu mieszania parami").

**M7. Mieszanie z tłem niemineralnym (plan Sekcja 4.3.2).** To nie nowy algorytm — to
M4/M5 z innym źródłem endmemberów (roślinność/cień/gleba zamiast drugiego minerału).
Niski koszt krańcowy po M5.

**M8. Mieszanki N-składnikowe (plan Sekcja 4.3.4).** Uogólnienie M4/M5 na N>2 z
próbkowaniem Dirichleta — świadomie na końcu tej warstwy, jak zaznaczono w planie
Sekcja 6.

## Warstwa 4 — poza zakresem fazy 1 (odłożone, jak w planie Sekcja 6/7)

**M9. Domena TIR/Ecostress (plan Sekcja 4.2)** — osobna fizyka, faza 2, zależna od
otwartego pytania #1 z planu.

**M10. Ścieżka generatywna (cGAN/diffusion/VAE)** — opcjonalny eksperyment poboczny,
zależny od otwartego pytania o liczbę replik per mineral (plan Sekcja 7).

## Warstwa 5 — spięcie w eksperymenty (plan Sekcja 5)

**M11. Harness eksperymentalny** — odtwarza metodykę ewaluacji artykułu (F1/recall, mapy
GT Cuprite, architektura FC_Baseline), żeby Eksperymenty 1, 2, 3, 5, 6 były bezpośrednio
porównywalne z Tabelą 3/4 oryginału. Wymaga minimum M1–M5 gotowych, żeby Eksperyment 1
(ablacja) miał co porównywać.

**M12. Raportowanie** — wskaźnik odrzuceń guardraila (Eksperyment 4), błąd odzysku
udziałów z unmixing (Eksperyment 7).

## Uwaga strukturalna

Obecny `src/` jest płaski (`main.py`, `db.py`), zgodnie z konwencją szablonu S&I dla
małych produktów. Przy ~12 modułach to się szybko zrobi nieczytelne — polecam w M1 (albo
zaraz po nim) przejść na `src/spectralforge/` jako właściwy pakiet z podpakietami
(`operators/`, `mixing/`, `db/`, `experiments/`) i zaktualizować `pyproject.toml`
(`packages = ["src/spectralforge"]`), zostawiając `src/main.py` jako cienki punkt wejścia
CLI.
