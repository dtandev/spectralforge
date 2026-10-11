# Plan badawczy — SpectralForge

Data: 2026-07-25
Punkt wyjścia: `docs/Moj_plan_na_to_repo.md` (plan autora) oraz Jabłońska, Zięba, Tanajewski,
*"Metric learning networks for accurate mineral detection with different augmentation
techniques"*, Expert Systems With Applications 304 (2026) 130692 (`docs/1-s2.0-S0957417425043076-main.pdf`).

<!-- TODO: verify this — dokument roboczy, do dyskusji i korekty przez autora. -->

## 1. Cel

SpectralForge ma być biblioteką do budowy dużych, zróżnicowanych zbiorów sygnatur
spektralnych per mineral z bibliotek referencyjnych (USGS, opcjonalnie Ecostress), na potrzeby
metod uczenia maszynowego operujących na podobieństwie widm (sieci syjamskie, metric learning,
one-class classification) — bezpośrednia kontynuacja podejścia z artykułu ESWA 2026.

W odróżnieniu od augmentacji w artykule, która służyła wyłącznie regularyzacji jednej
konkretnej sieci metric-learning, SpectralForge ma ambicję być narzędziem ogólnego przeznaczenia:
wygenerowane sygnatury mogą trafić do dowolnego downstream modelu. To podnosi poprzeczkę —
jeśli augmentacja nie oddaje fizyki, błąd nie zostaje "wchłonięty" przez jeden konkretny
eksperyment, tylko powiela się we wszystkich zastosowaniach zbioru.

## 2. Rama narracyjna — jak pozycjonować SpectralForge względem artykułu

Ten projekt nie jest erratą do artykułu ESWA 2026 — jest realizacją agendy, którą artykuł
sam sobie wyznaczył. Sekcja 7 artykułu ("Conclusion and future work") formułuje wprost:

> "Future work may explore generalizing the approach to work with data from any satellite
> provider, incorporating additional data augmentation techniques, adding more minerals to
> the training dataset, or testing alternative metric learning loss functions... Another
> important direction would be a systematic comparison of augmentation strategies, for
> example, evaluating the effect of removing individual augmentation steps or identifying
> the most effective augmentation configurations... future studies should evaluate the model
> in different geological environments and mineral deposits beyond the Cuprite region."

To jest dokładnie zakres tego planu: systematyczne porównanie strategii augmentacji
(Eksperyment 1), rozszerzenie na więcej minerałów (Eksperyment 3), generalizacja
międzysensorowa i poza Cuprite (Eksperymenty 5–6). Dwie konsekwencje tej ramy:

- **Ton wobec artykułu:** SpectralForge *systematyzuje i ugruntowuje fizycznie* etap
  augmentacji, którego wersja pilotażowa w artykule była pragmatycznym pierwszym podejściem,
  wystarczającym do wykazania wykonalności metody (proof-of-concept) w wąskim,
  kontrolowanym benchmarku (Cuprite/EMIT, 4 minerały). To, że niektóre operatory (A1, A3,
  A5, A6) upraszczają fizykę, nie unieważnia wyniku artykułu — pokazuje raczej, że wynik
  był osiągnięty *mimo* uproszczeń, co samo w sobie jest ciekawym punktem wyjścia: ile
  jeszcze można zyskać, gdy augmentacja faktycznie odda fizykę stojącą za zjawiskiem.
- **Ton wobec rozszerzeń poza artykuł:** to, co wykracza poza literalne future-work artykułu
  (Sekcja 4.3: unmixing, tło niemineralne, wielkość ziarna, mieszanki N-składnikowe,
  ścieżka generatywna) nie jest przedstawiane jako "brakujące w artykule", tylko jako
  budowa **ogólnej infrastruktury dla spektroskopii mineralnej**, w której artykuł pełni
  rolę benchmarku walidacyjnego (ten sam obszar Cuprite/EMIT, ta sama metodyka F-score),
  a nie punktu krytyki.

Praktyczna wskazówka na przyszłość (np. przy pisaniu kolejnego paperu lub README): wyniki
warto raportować jako *ablację/rozszerzenie* ("we extend the augmentation ablation study
proposed in [ref]"), nie jako poprawkę błędu — to jednocześnie uczciwsze wobec faktycznego
wkładu artykułu (solidny wynik na trudnym zadaniu one-class) i bardziej neutralne wobec
współautorów.

## 3. Krytyka metod augmentacji z artykułu (uzasadnienie zmian)

Poniższa tabela podsumowuje operatory A1–A7 z artykułu (Sekcja 3.4) i ocenę ich zasadności
fizycznej.

| Operator | Co robi (wg artykułu) | Problem fizyczny |
|---|---|---|
| A1 Scaling | `x·a`, `a~U(0.5,1.5)` — symuluje zmiany oświetlenia | Odbicie powierzchniowe po korekcji atmosferycznej z definicji ma być niezmiennicze względem oświetlenia; szerokie skalowanie miesza domenę radiancji z domeną odbicia i może wypchnąć wartości poza fizyczny zakres [0,1] |
| A2 Distortion | `x + b·x`, `b~N(0,σ²)` | Generyczny szum mnożnikowy — nie jest przypisany do konkretnego zjawiska fizycznego, ale też nie łamie żadnej zasady wprost |
| A3 Rotation | Obrót wokół średniej o kąt θ z dyskretnego zbioru | **Brak uzasadnienia fizycznego.** To transformacja afiniczna nazwana "rotacją" przez analogię do augmentacji obrazów w CV — widmo 1D nie ma symetrii obrotowej jak obraz 2D. Żaden znany proces (kalibracja, atmosfera, BRDF) nie "obraca" widma w ten sposób |
| A4 Rolling | Średnia krocząca, okno 2–6 pasm | Fizycznie tłumaczalne jako spadek rozdzielczości spektralnej, ale okno porównywalne z szerokością wąskich cech diagnostycznych (Rys. 4) — koliduje z deklarowanym celem "preserving diagnostic absorption features" |
| A5 Noise addition | Gaussowski szum, jedna wariancja globalna dla wszystkich pasm | Realny szum detektora (NEdR) jest silnie zależny od długości fali i poziomu sygnału (VNIR vs SWIR, okna absorpcji atmosferycznej) — model jednorodny to nadmierne uproszczenie |
| A6 Drift mixing | Mieszanie dwóch widm z zachowaniem "characteristic absorption ranges" 1:1 ze spektrum źródłowego | **Łamie fizykę mieszania.** Mieszanie arealne (Boardman 1993) jest liniowe jednolicie na całym zakresie widmowym; mieszanie intymne (Hapke 2012) jest nieliniowe w odbiciu, liniowe dopiero w przestrzeni single-scattering albedo. Twarde "zamrażanie" pasm diagnostycznych nie odpowiada żadnemu z tych modeli — sztucznie zachowuje pełną głębokość cechy, podczas gdy w realnym pikselu mieszanym cecha powinna być stłumiona |
| A7 Linear mixing | Klasyczne mieszanie liniowe `α·x1+(1-α)·x2+szum`, z opcjonalnym continuum removal | Sam wzór mieszania jest poprawny (to standardowy model arealny) — problem pojawia się dopiero przy zastosowaniu continuum removal do syntetycznego zmieszanego widma: Rys. 6 pokazuje wynik >1.3 odbicia, wartość fizycznie niemożliwą |

**Wniosek:** trzy operatory (A3, A6, A5) w obecnej formie nie oddają dobrze fizyki stojącej za
procesem, a A1+A7 w połączeniu z continuum removal generują obserwowalne artefakty
(Rys. 6, wynik Calcite: F1 spada z 0.343 do 0.146 po continuum removal — sami autorzy piszą,
że wynika to z płytkich cech absorpcyjnych Calcite będących wrażliwymi na normalizację
kontinuum). To bezpośrednio motywuje przeprojektowanie augmentacji w SpectralForge (patrz
Sekcja 2 w sprawie tonu tej rewizji).

## 4. Poprawiony zestaw operatorów augmentacji

Każdy operator poniżej (oznaczony B1–B8, żeby odróżnić od A1–A7 artykułu) zastępuje
odpowiednik z artykułu jawnym, fizycznie umotywowanym modelem, zapisanym w tej samej
notacji co artykuł (x ∈ R^d — widmo, λ_i — środkowa długość fali i-tego pasma, μ(x) —
wartość średnia odbicia). Parametry oznaczone `TODO: verify this` wymagają dowiązania do
rzeczywistych danych pomiarowych, a nie arbitralnych zakresów.

### 4.1 Domena VNIR-SWIR (biblioteka USGS)

**B1 — Oświetlenie / topografia** (zastępuje A1 Scaling).
Model kosinusowy kąta padania (korekcja Lambertowska, standard w teledetekcji terenu
zróżnicowanego topograficznie):

```
x_B1 = clip( x · [cos(θ_i) / cos(θ_ref)],  0, 1 )
θ_i ~ U(θ_min, θ_max)
```

`θ_i` — kąt padania promieni słonecznych względem normalnej terenu, losowany z zakresu
wyprowadzonego z rzeczywistych metadanych sceny (kąt Słońca + nachylenie terenu) dla
docelowego regionu, a nie z arbitralnego przedziału. `θ_ref` — kąt referencyjny pomiaru
laboratoryjnego widma USGS (typowo 0°, pomiar nadirowy). Wynik przycinany do [0,1] —
usuwa artefakt z Rys. 6 artykułu (odbicie >1).

**B2 — Szum sensora** (zastępuje A5 Noise addition, częściowo A2 Distortion).
Wariancja szumu jako funkcja pasma i poziomu sygnału zamiast jednej globalnej wariancji:

```
x_B2,i = x_i + n_i,     n_i ~ N(0, σ_i²)
σ_i²   = σ_read²(λ_i) + k · x_i
```

`σ_read(λ_i)` — z opublikowanej krzywej NEdR (noise-equivalent-delta-reflectance) danego
sensora (EMIT/AVIRIS) `TODO: verify this — potwierdzić dostępność publicznej krzywej NEdR`;
`k·x_i` — składnik śrutowy (shot noise) proporcjonalny do sygnału.

**B3 — Rozdzielczość spektralna / resampling** (zastępuje A4 Rolling).
Konwolucja z rzeczywistą funkcją odpowiedzi instrumentu (Instrument Line Shape) zamiast
arbitralnej średniej kroczącej:

```
x_B3,i = Σ_k x_k · g(λ_k - λ_i; FWHM_i),     Σ_k g(·) = 1
```

`g` — znormalizowane jądro Gaussa o szerokości `FWHM_i` z dokumentacji instrumentu. To samo
narzędzie służy zarówno do symulacji spadku rozdzielczości, jak i do właściwego resamplingu
USGS (rozdzielczość laboratoryjna) → siatka pasm EMIT/Ecostress.

**B4 — Dryft kalibracji długości fali** (zastępuje A3 Rotation).
Przesunięcie i rozciągnięcie osi λ, interpolacja widma na nową siatkę:

```
λ'_i = λ_i + δ + γ·(λ_i - λ_c)
δ ~ U(-Δ, Δ),    γ ~ U(-ε, ε)
x_B4 = interp(x, λ, λ')
```

`Δ, ε` — z opublikowanej niepewności kalibracji spektralnej sensora (rząd wielkości: ułamek
do kilku nm), nie arbitralny kąt "rotacji" bez odpowiednika fizycznego.

**B5 — Maskowanie pasm atmosferycznych** (formalizuje pozycję 5 z Tabeli 1 artykułu).
Deterministyczne, nie losowe — okna wynikają z fizyki atmosfery, nie z arbitralnego losowania:

```
x_B5,i = x_i · m_i
m_i = 0   jeśli λ_i ∈ {940±10, 1140±10, 1380±20, 1900±30, 2500±20} nm
m_i = 1   w przeciwnym razie
```

Granice okien do potwierdzenia względem faktycznej maski ważności pasm EMIT/AVIRIS
(`TODO: verify this`).

**B6 — Mieszanie arealne (liniowe)** (zastępuje A7, bez wyjątku z A6).
Pełne, jednolite mieszanie liniowe na **wszystkich** pasmach jednakowo:

```
x_B6 = α·x_1 + (1-α)·x_2 + n,     α ~ U(0,1),    n ~ N(0, σ_mix²)
```

Bez specjalnego "zamrażania" okien diagnostycznych obecnego w A6 artykułu.

**B7 — Mieszanie intymne (nieliniowe, Hapke)** (nie ma odpowiednika w artykule).
Konwersja odbicia do single-scattering albedo, liniowe mieszanie w tej przestrzeni, konwersja
z powrotem — jedyny fizycznie poprawny sposób modelowania mieszanin granularnych:

```
w_j = 1 - [(1 - x_j) / (1 + x_j)]²                      (odwrócenie r↔w, rozpraszanie izotropowe)
w_mix = Σ_j F_j · w_j,   F_j = (M_j / (ρ_j·D_j)) / Σ_k (M_k / (ρ_k·D_k))
x_B7 = (1 - √(1 - w_mix)) / (1 + √(1 - w_mix))
```

`M_j` — udział masowy, `ρ_j` — gęstość, `D_j` — średnia średnica ziarna składnika j.
`TODO: verify this` — to uproszczone przybliżenie relacji Hapke r↔w dla izotropowych
rozpraszaczy (bez funkcji fazowej, bez efektu hot-spot/shadow-hiding); dokładny wariant do
potwierdzenia względem Hapke (2012), *Theory of Reflectance and Emittance Spectroscopy*,
przed użyciem w publikacji. Ten sam mechanizm (zmiana tylko `D_j`, stałe `M_j`) daje serie
wielkości ziarna dla pojedynczego minerału — patrz 4.3.3.

**B8 — Walidacja fizyczna (guardrail)** (brak odpowiednika w artykule; adresuje artefakt
z Rys. 6). Nie jest transformacją, tylko zbiorem twardych ograniczeń nakładanych na wynik
każdego z operatorów B1–B7:

```
0 ≤ x_B*,i ≤ 1                          dla wszystkich i
kontinuum(x_B*) — wypukła otoczka górna   (test przed/po continuum removal)
naruszenie → odrzucenie próbki / ponowne losowanie parametrów
```

### 4.2 Domena TIR (Ecostress, jeśli włączona do zbioru)

Ecostress dostarcza głównie emisyjność, nie odbicie — inna fizyka (prawo Kirchhoffa,
emisja termiczna, separacja temperatura-emisyjność). Augmentacje z sekcji 4.1 **nie
przenoszą się wprost**. Jeśli SpectralForge ma faktycznie łączyć USGS i Ecostress:

- Osobny moduł augmentacji dla emisyjności (np. perturbacja temperatury powierzchni +
  przeliczenie promieniowania Plancka, a nie mnożenie/mieszanie wartości emisyjności
  jak gdyby to było odbicie).
- Jasne oznaczenie w `product.yaml`/dokumentacji, które operatory dotyczą której domeny.
- `TODO: verify this` — do ustalenia z autorem, czy na start zakres projektu ogranicza się
  do VNIR-SWIR (USGS) i moduł TIR/Ecostress zostaje jako faza 2, żeby nie rozmywać zakresu
  pierwszej iteracji.

### 4.3 Operacje wykraczające poza artykuł (rozszerzenia)

Artykuł ogranicza się do augmentacji na potrzeby jednej sieci metric-learning w zadaniu
one-class. Poniższe operacje wykraczają poza ten zakres — część to w ogóle inny rodzaj
operacji (analiza/inferencja, nie augmentacja), część to naturalne rozszerzenia modułu
Hapke już zaplanowanego w 4.1.7. Zgodnie z ramą z Sekcji 2, te punkty pozycjonujemy jako
wkład infrastrukturalny dla dziedziny, nie jako brakujące elementy artykułu.

1. **Unmixing (operacja odwrotna do mieszania).** Dekompozycja zmieszanego/złożonego widma
   na udziały składowych endmemberów (klasyczne NNLS/FCLS dla mieszania liniowego, lub
   odmieszanie w przestrzeni SSA dla modelu Hapke). Dwie role w SpectralForge:
   - **Walidacja pipeline'u**: zmieszaj znane widma → odmieszaj → sprawdź, czy odzyskane
     udziały zgadzają się z zadanymi (sanity check dla całego modułu mieszania z 4.1.6/4.1.7).
   - **Generowanie danych z etykietą udziału**: pozwala budować zbiory treningowe do zadania
     regresji udziałów (abundance estimation), a nie tylko klasyfikacji one-class — realne
     rozszerzenie zastosowań SpectralForge poza to, co testuje artykuł.
2. **Mieszanie z tłem niemineralnym.** Artykuł miesza wyłącznie minerał z minerałem, ale
   realne piksele satelitarne (widoczne nawet na Rys. 9–10 artykułu) niemal zawsze zawierają
   kontaminację roślinnością, cieniem lub glebą. Dodać endmembery tła (roślinność, cień,
   gleba) z bibliotek spektralnych i mieszać je z sygnaturami mineralnymi tym samym modułem
   liniowym/Hapke z 4.1.6–4.1.7 — realistyczny scenariusz kompletnie pominięty w oryginale.
3. **Serie wielkości ziarna (grain-size) via Hapke.** Moduł Hapke z 4.1.7 pozwala też — bez
   dodatkowego mieszania międzyklasowego — wygenerować wewnątrzklasową zmienność
   *pojedynczego* minerału: drobne ziarno daje płytszą i szerszą cechę absorpcyjną, grube
   ziarno głębszą i węższą (zmiana `D_j` przy stałym `M_j` we wzorze z 4.1.7). Artykuł w
   ogóle nie modeluje wielkości ziarna, a to jedno z głównych naturalnych źródeł zmienności
   widm minerałów w terenie.
4. **Mieszanki N-składnikowe (N>2).** Uogólnienie mieszania z artykułu (tylko pary widm) na
   mieszanki 3+ składników z udziałami próbkowanymi z rozkładu Dirichleta — bliższe realnej
   heterogeniczności subpikselowej niż założenie "zawsze dokładnie dwa minerały".

**Rozważone i odłożone: generatywna augmentacja (cGAN/diffusion, VAE latent perturbation).**
Tabela 1 artykułu wymienia te techniki (pozycje 11–12) jako uznane w literaturze, ale sami
autorzy ich nie testują — to jawna luka. W przeciwieństwie do punktów 1–4 powyżej, to inna
filozofia niż reszta Sekcji 4: model wyuczony (czarnoskrzynkowy) zamiast jawnego równania
fizycznego. Główne ryzyko: biblioteka USGS ma niewiele replik na minerał (rząd
kilku–kilkunastu widm per klasa — `TODO: verify this`, do potwierdzenia rzeczywistą liczbą),
co przy tak małym zbiorze grozi mode collapse lub halucynowaniem widm łamiących fizykę
kontinuum — dokładnie ten problem, przed którym uciekamy rezygnując z A3/A6 z artykułu.
Nie włączono do Sekcji 4.1 jako operator podstawowy; jeśli ma być badane, to jako osobna
ścieżka eksperymentalna porównawcza (patrz Eksperyment 10 w Sekcji 5) z wynikami zawsze
przepuszczonymi przez guardrail fizyczny (4.1.8) przed jakimkolwiek użyciem w treningu.

## 5. Plan eksperymentów — rozszerzenie testów z artykułu

Poniższe eksperymenty są zaprojektowane jako bezpośrednie, odtwarzalne rozszerzenie
Sekcji 4–5 artykułu, korzystając z tego samego obszaru walidacji (Cuprite, EMIT) i tej samej
metodyki ewaluacji (F-score/recall wg map GT Swayze et al. 2008), żeby wyniki były
porównywalne 1:1 z Tabelą 3/4 oryginału.

1. **Ablacja fizyczna operator-po-operatorze.** Zastąpić każdy z A1–A7 jego fizycznie
   umotywowanym odpowiednikiem B1–B8 z Sekcji 4.1, jeden na raz, i porównać F1/recall
   względem bazowych wyników artykułu (Tabela 3) przy identycznej architekturze
   (FC_Baseline) i funkcji straty. Hipoteza: fizycznie poprawne augmentacje poprawiają
   generalizację przy zachowanej lub lepszej precyzji, szczególnie dla minerałów o
   subtelnych cechach (Jarosite, Kaolinite wg dyskusji autorów).
2. **Test na Calcite z mieszaniem Hapke.** Autorzy odnotowują, że continuum removal
   *pogarsza* wynik dla Calcite (płytkie cechy absorpcyjne, F1 0.343→0.146). Hipoteza:
   właściwe mieszanie intymne (B7, Hapke) zamiast A6/A7 naturalnie odda tłumienie płytkich
   cech bez potrzeby agresywnej normalizacji kontinuum, co powinno poprawić stabilność
   wyniku dla Calcite.
3. **Rozszerzenie na pełny zestaw 7 minerałów PCD.** Artykuł wspomina o przygotowaniu
   danych dla siedmiu minerałów porfirowych złóż miedzi (alunite, chlorite, calcite,
   goethite, hematite, jarosite, kaolinite — Sekcja 4.1 artykułu), ale Tabela 3 raportuje
   wyniki tylko dla 4 (Alunite, Jarosite, Kaolinite, Calcite). Naturalne rozszerzenie:
   dokończyć ewaluację dla Chlorite, Goethite, Hematite tą samą metodyką.
4. **Metryka wiarygodności fizycznej.** Wprowadzić automatyczny raport ułamka wygenerowanych
   próbek augmentacji odrzuconych przez guardrail (B8, pkt 4.1.8) — nowy, brakujący w
   oryginale wskaźnik jakości pipeline'u augmentacji, niezależny od downstream F1-score.
5. **Generalizacja międzysensorowa.** Ponieważ resampling do siatki EMIT ma być oparty o
   rzeczywistą funkcję odpowiedzi instrumentu (B3, pkt 4.1.3), przetestować, czy model
   wytrenowany na sygnaturach SpectralForge generalizuje bez ponownego treningu na dane z
   innego sensora (np. PRISMA lub AVIRIS-NG) lepiej niż przy podejściu ze średnią kroczącą
   z artykułu.
6. **Oświetlenie/topografia vs. wynik na terenie złożonym.** Porównać model trenowany na A1
   (skalowanie globalne) vs. model kosinusowy (B1, pkt 4.1.1) pod kątem transferu na
   bardziej zróżnicowany topograficznie fragment sceny Cuprite.
7. **Walidacja mieszania przez odmieszanie.** Dla modułu liniowego (B6, 4.1.6) i Hapke
   (B7, 4.1.7): zmieszać znane widma z zadanymi udziałami, odmieszać (NNLS / odmieszanie w
   SSA), zmierzyć błąd odzyskanych udziałów. To niezależny od F1-score test poprawności
   samego mechanizmu mieszania (pkt 4.3.1) — brakujący w oryginale krok kontroli jakości.
8. **Wpływ kontaminacji tłem na odporność detekcji.** Porównać F1/recall modelu trenowanego
   wyłącznie na mieszankach minerał-minerał (jak w artykule) vs. modelu trenowanego z
   dodatkiem tła niemineralnego (4.3.2), ewaluowanego na tych samych mapach GT Cuprite.
   Hipoteza: model z tłem lepiej generalizuje na realne piksele satelitarne, gdzie
   kontaminacja roślinnością/cieniem jest normą, a nie wyjątkiem.
9. **Separowalność wewnątrzklasowa przy zmiennej wielkości ziarna.** Wygenerować serie
   grain-size (4.3.3) dla każdego z 4 (docelowo 7) minerałów i sprawdzić, czy embedding
   sieci metric-learning z artykułu klastruje je poprawnie jako tę samą klasę mimo zmiennej
   głębokości cechy — test odporności embeddingu na realną zmienność teksturalną, nie tylko
   syntetyczny szum.
10. **Augmentacja fizyczna vs. augmentacja wyuczona (generatywna).** Jeśli zdecydujemy się
    rozwijać ścieżkę z cGAN/diffusion/VAE (patrz 4.3, "Rozważone i odłożone"): wytrenować
    wspólny model generatywny warunkowany klasą na połączonych danych wszystkich minerałów
    (żeby zwiększyć efektywny rozmiar zbioru), porównać odsetek próbek odrzuconych przez
    guardrail fizyczny (B8, 4.1.8) oraz końcowy F1 względem operatorów B1–B7 z Sekcji 4.1.
    Traktować jako eksperyment poboczny/opcjonalny, nie jako zamiennik głównej ścieżki
    fizycznej.

## 6. Zakres i granice (co NIE wchodzi w pierwszą iterację)

- Moduł TIR/Ecostress — odłożony do fazy 2 (patrz 4.2), żeby nie mieszać dwóch różnych
  fizyk w jednym pierwszym wydaniu.
- Model Hapke (B7) ograniczony do przybliżenia izotropowego multiple-scattering — pełny
  model anizotropowy (funkcja fazowa, efekty hot-spot) poza zakresem na start; oznaczyć
  jako znane uproszczenie w `product.yaml` → `limitations`.
- Brak własnych pomiarów terenowych/laboratoryjnych — cały zbiór bazuje na bibliotekach
  referencyjnych (USGS, opcjonalnie Ecostress) i modelach fizycznych, nie na nowych pomiarach.
- Generatywna augmentacja (cGAN/diffusion, VAE latent perturbation) — odłożona jako
  eksperyment poboczny (Eksperyment 10), nie część głównego zestawu operatorów, ze względu
  na ryzyko halucynacji przy małej liczbie replik per minerał w bibliotece USGS.
- Mieszanki N-składnikowe (4.3.4) i unmixing (4.3.1) — wymagają najpierw stabilnego modułu
  mieszania parami (4.1.6/4.1.7); traktować jako rozszerzenie fazy 1, nie jako blocker startu.

## 7. Otwarte pytania do autora

- Czy Ecostress wchodzi w zakres fazy 1, czy zostaje odłożony do fazy 2 (zalecane wyżej)?
- Czy dysponujemy dostępem do rzeczywistej krzywej NEdR dla EMIT (dokumentacja misji/JPL),
  czy trzeba ją oszacować z danych scenowych?
- Czy porównanie ma odtwarzać dokładnie architekturę FC_Baseline z artykułu, czy repo ma
  od razu testować własne architektury metric-learning?
- Priorytet: najpierw pełna implementacja fizycznych operatorów (Sekcja 4), czy najpierw
  ablacja na już istniejących 4 minerałach z artykułu, żeby szybko zweryfikować hipotezę
  przed rozbudową zakresu na 7 minerałów?
- Czy biblioteki tła niemineralnego (roślinność, cień, gleba) dla punktu 4.3.2 mają być
  brane z USGS (ten sam format, prostsza integracja) czy z innego źródła?
- Ile realnie replik na minerał ma biblioteka USGS dla naszych 7 minerałów PCD? To rozstrzyga,
  czy ścieżka generatywna (Eksperyment 10) jest w ogóle metodologicznie sensowna, czy z góry
  skazana na przeuczenie.
- Dokładny wariant relacji Hapke r↔w użyty w B7 (4.1.7) jest uproszczonym przybliżeniem
  izotropowym — czy akceptowalny na start, czy warto od razu sięgnąć po pełniejszą
  formę z Hapke (2012) z funkcją fazową?
