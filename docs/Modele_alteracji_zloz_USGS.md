# Modele alteracji złóż mineralnych — katalog USGS

Data: 2026-07-25
Źródło zbiorcze: du Bray, E.A., ed., 1995, *Preliminary Compilation of Descriptive
Geoenvironmental Mineral Deposit Models*, U.S. Geological Survey Open-File Report 95-831
(https://pubs.usgs.gov/of/1995/ofr-95-0831/, spis treści:
https://pubs.usgs.gov/of/1995/ofr-95-0831/CONTENTS.pdf) — reformatowana, rozszerzona
wersja oryginalnego katalogu Cox, D.P., and Singer, D.A., eds., 1986, *Mineral Deposit
Models*, U.S. Geological Survey Bulletin 1693, 379 p.
(https://pubs.usgs.gov/bul/b1693/Intro.pdf). Modele numerowane wg oryginalnej numeracji
Cox & Singer (1986). Każda sekcja poniżej ma własne, pełne źródła (autorzy rozdziału +
bezpośredni URL do PDF + kluczowa literatura geologiczna, na której oparty jest dany
model) w bloku "Źródła" na końcu sekcji.

Kontekst: `docs/Plan_generator_scen_SpectralForge.md` (Faza 3 — generator scen), dyskusja
o modelu Lowella-Guilberta i bibliotece `geone` (MPS). Każdy wpis poniżej to jeden
potencjalny "szkielet geologiczny" (geometria + topologia stref + mineralogia) do
wykorzystania przy generowaniu syntetycznych map alteracji.

<!-- TODO: verify this — treść wiernie streszcza sekcje "Wall-rock alteration" i "Ore and
gangue mineralogy and zonation" z cytowanych rozdziałów; zweryfikowano bezpośrednio ze
źródła (nie z pamięci), ale to wciąż skrót, nie pełny tekst oryginału. -->

## Jak czytać ten katalog

Dla każdego modelu: geometria strefowania (co jest kluczowe dla generatora — koncentryczna
wokół intruzji, komin/rura pionowa, czy liniowa wzdłuż uskoku/żyły), sekwencja stref z
mineralogią, minerały wtórne/supergeniczne (najbardziej istotne dla wykrywalności VNIR-SWIR),
oraz źródło.

---

## 1. Porphyry Cu deposits (Model 17)

*Cox, L.J., Chaffee, M.A., Cox, D.P., and Klein, D.P., in du Bray (1995), Chapter 11 (p. 75–89).*

**Geometria:** koncentryczna, wokół stoku porfirowego (intruzji).

**Strefowanie (od spodu/rdzenia na zewnątrz):**
sodowo-wapniowa (oligoklaz/albit, aktynolit, sfen) → potasowa (skaleń potasowy, biotyt,
rutyl, piryt lub magnetyt) → propylityczna (oligoklaz/albit, epidot lub kalcyt, chloryt,
rutyl, magnetyt lub piryt). Fylityczna (serycyt, chloryt, rutyl, piryt) i argilityczna
(ił, serycyt, chloryt, piryt) mogą nakładać się na wcześniejsze zespoły potasowe.
**Alteracja wysokoglinowa (pirofillit, alunit, andaluzyt, korund, diaspor, ił, serycyt)
może występować w górnej części niektórych złóż** — to dokładnie nakładka typu lithocap.
Strefy propylityczna/fylityczna zwykle leżą na flankach złoża.

**Cytat dosłowny (p. 77):** *"Alteration zones (and mineral assemblages), from bottom,
innermost zones outward are: sodic-calcic... potassic... to propylitic... Phyllic...
and argillic... alteration may overprint early potassic assemblages. High-alumina
alteration (pyrophyllite, alunite, andalusite, corundum, diaspore, clay, and sericite)
may be present in upper part of some deposits."*

**Źródła:**
- Cox, L.J., Chaffee, M.A., Cox, D.P., and Klein, D.P., 1995, Porphyry Cu deposits (Model 17), *in* du Bray, E.A., ed., Preliminary compilation of descriptive geoenvironmental mineral deposit models: U.S. Geological Survey Open-File Report 95-831, p. 75–89. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP11.pdf
- Cox, D.P., 1986, Descriptive model of porphyry Cu deposits, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693.
- Lowell, J.D., and Guilbert, J.M., 1970, Lateral and vertical alteration-mineralization zoning in porphyry ore deposits: Economic Geology, v. 65, p. 373–408. (pierwotne źródło modelu zonacji)
- Gustafson, L.B., and Hunt, J.P., 1975, The porphyry copper deposit at El Salvador, Chile: Economic Geology, v. 70, p. 857–912.

---

## 2. Cu, Au, and Pb-Zn skarn deposits (Models 18b, 18c)

*Hammarstrom, J.M., et al., in du Bray (1995), Chapter 12 (p. 90–111).*

**Geometria:** strefowanie kontaktowe wokół intruzji wciśniętej w skały węglanowe;
egzoskarn (strona skały węglanowej) vs. endoskarn (strona intruzji).

**Strefowanie:** rogowce (hornfels, szeroko rozwinięte, do 15–20 km²), marmur, wybielony
wapień, strefy skarnowe; zespoły potasowy, serycytowy, argilityczny, propylityczny;
"fronty" krzemionkowe/marmurowe — ostre granice między skałą nieprzeobrażoną a zmienioną.

**Zonacja rudna (prograde → retrograde → ruda):**
- Cu-skarn: piroksen (diopsyd-hedenbergit), granat (andradyt-grossular), wollastonit →
  aktynolit, chloryt, ił, epidot → chalkopiryt, piryt, hematyt, magnetyt, sfaleryt, galena,
  arsenopiryt.
- Au-skarn: granat, piroksen, idokraz, wollastonit → epidot, amfibol, chloryt, prehnit,
  skapolit, minerały boru, skaleń potasowy, ił, syderyt → złoto (elektrum), piryt,
  pirotyn, chalkopiryt, arsenopiryt, magnetyt, hematyt (specularyt), sfaleryt, galena.
- Zn-Pb skarn: piroksen (hedenbergit-johannsenit), granat (andradyt-spessartyn), bustamit,
  rodonit → aktynolit (Mn-bogaty), ilvait, chloryt, dannemoryt, rodochrozyt, epidot →
  sfaleryt, galena, pirotyn, piryt, magnetyt, chalkopiryt, arsenopiryt.

**Źródła:**
- Hammarstrom, J.M., Kotlyar, B.B., Theodore, T.G., Elliott, J.E., John, D.A., Doebrich, J.L., Nash, J.T., Carlson, R.R., Lee, G.K., Livo, K.E., and Klein, D.P., 1995, Cu, Au, and Zn-Pb skarn deposits (Models 18b,c), *in* du Bray (1995), p. 90–111. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP12.pdf
- Cox, D.P., and Theodore, T.G., 1986; Cox, D.P., 1986; Theodore, T.G., and others, 1991 — descriptive models, U.S. Geological Survey Bulletin 1693 / Bulletin 2004.
- Einaudi, M.T., Meinert, L.D., and Newberry, R.J., 1981, Skarn deposits: Economic Geology 75th Anniversary Volume, p. 317–391. (klasyfikacja skarnów cytowana w Fig. 1)
- Meinert, L.D., 1983, Variability of skarn deposits — Guides to exploration: Geological Association of Canada Special Paper.

---

## 3. Fe skarn deposits (Model 18d)

*Hammarstrom, J.M., et al., in du Bray (1995), Chapter 13 (p. 112–120).*

**Geometria:** j.w. (kontaktowa), ale gospodarzem jest magnetyt masowy, nie kruszec bazowy.

**Strefowanie:** endoskarn wapniowy — albit, ortoklaz, epidot, kwarc, skapolit; endoskarn
magnezowy — minimalny, dominują zespoły propylityczne.

**Zonacja rudna:**
- Wapniowy Fe-skarn: granat (grossular-andradyt), piroksen (ferrosalit) → amfibol, chloryt,
  epidot → magnetyt, chalkopiryt, kobaltyn, pirotyn.
- Magnezowy Fe-skarn: forsteryt, kalcyt, spinel, diopsyd, magnetyt, apatyt → amfibol,
  humit, serpentyn, flogopit, talk, chloryt, magnezyt → magnetyt, piryt, chalkopiryt,
  sfaleryt, pirotyn, arsenopiryt.
- Skapolitowo-(albitowy) Fe-skarn: granat, piroksen → skapolit, albit, chloryt, kalcyt,
  zeolity, aktynolit, epidot → magnetyt, **hematyt**, piryt, markasyt, chalkopiryt,
  sfaleryt, pirotyn, arsenopiryt.

**Minerały wtórne (p. 118):** *"Magnetite may alter to **hematite, maghemite, goethite,
limonite, or lepidocrocite** during oxidation and weathering."* — bezpośrednie
przejście magnetyt→getyt/hematyt przy wietrzeniu.

**Źródła:**
- Hammarstrom, J.M., Theodore, T.G., Kotlyar, B.B., Doebrich, J.L., Elliott, J.E., Nash, J.T., John, D.A., and Livo, K.E., 1995, Fe skarn deposits (Model 18d), *in* du Bray (1995), p. 112–120. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP13.pdf
- Cox, D.P., 1986, Descriptive model of Fe skarn deposits, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693, p. 94.
- Einaudi, M.T., Meinert, L.D., and Newberry, R.J., 1981, Skarn deposits: Economic Geology 75th Anniversary Volume, p. 317–391.
- Zitzmann, Arnold, 1977, The iron ore deposits of the western U.S.S.R., *in* Zitzmann, A., ed., The iron ore deposits of Europe and adjacent areas: Hannover, Bundesanstalt für Geowissenschaften und Rohstoffe, v. 1, p. 325–391.

---

## 4. Volcanic-associated massive sulfide (VMS) deposits (Models 24a-b, 28a)

*Taylor, C.D., et al., in du Bray (1995), Chapter 16 (p. 137–151).*

**Geometria:** **komin/rura pionowa** (alteration pipe) pod soczewką masywnych siarczków —
zupełnie inna geometria niż koncentryczne pierścienie wokół intruzji. Trzy podtypy: Cyprus
(mafitowy), Kuroko (felzytowy, arc), Besshi (wulkaniczno-osadowy).

**Strefowanie (od rdzenia komina w górę/na zewnątrz):** rdzeń chlorytowo-siarczkowy
(Cpy±Py±Po, alteracja chlorytowa) → otoczka serycytowo-kwarcowa (Py+Sp±Gn, alteracja
sercytowo-chlorytowa w strefie stockwork) → soczewka masywnych siarczków na górze
(Sp+Gn+Py+Ba, silna zonacja chemiczna). Metal zoning: miedź w footwall/stringer, cynk
rośnie ku górze/na zewnątrz od rdzenia, ołów/arsen/antymon wzbogacone dalej na zewnątrz
w złożach felzytowych (Kuroko), baryt/krzemionka wzbogacone ku stropowi.

**Cytat (p. 139):** *"The most common alteration is pervasive chloritization, which is
less well developed with increasing depth and distance from hydrothermal upwelling
zones... Deposits hosted by felsic rocks typically have extensively developed quartz
sericite alteration in the footwall."*

**Minerały wtórne (p. 140):** gossan żelazisty; w klimacie umiarkowanym: **getyt**, krzemionka
amorficzna/krystaliczna, **jarosit**, plumbojarosit, argentojarosit, beudantyt i inne
uwodnione siarczany-hydroksysiarczany metali.

**Źródła:**
- Taylor, C.D., Zierenberg, R.A., Goldfarb, R.J., Kilburn, J.E., Seal, R.R., II, and Kleinkopf, M.D., 1995, Volcanic-associated massive sulfide deposits (Models 24a-b, 28a), *in* du Bray (1995), p. 137–151. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP16.pdf
- Singer, D.A., 1986a,b, Descriptive models of Cyprus/Kuroko massive sulfide; Cox, D.P., 1986, Descriptive model of Besshi massive sulfide — *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693.
- Franklin, J.M., Sangster, D.M., and Lydon, J.W., 1981, Volcanic-associated massive sulfide deposits: Economic Geology 75th Anniversary Volume, p. 485–626.
- Lydon, J.W., 1984, Volcanogenic massive sulphide deposits, Part 1 — A descriptive model: Geoscience Canada, v. 11, p. 195–202. (źródło diagramu "alteration pipe", Fig. 1)
- Slack, J.F., 1993, Descriptive and grade-tonnage models for Besshi-type massive sulfide deposits, *in* Kirkham, R.V., and others, eds., Mineral deposit modeling: Geological Association of Canada Special Paper 40, p. 343–372.

---

## 5. Creede, Comstock, Sado epithermal vein deposits — niskosulfidacyjne (Models 25b,c,d)

*Plumlee, G.S., et al., in du Bray (1995), Chapter 18 (p. 152–161).*

**Geometria:** żyły/stockworki w skałach wulkanicznych pośrednio-felzytowych, silna
zonacja pionowa i boczna wzdłuż żył (nie koncentryczna wokół punktu, tylko wzdłuż
struktury żyłowej — patrz Fig. 1: "Bonanza ores" blisko powierzchni → żyłowa ruda głębiej
→ potasowa alteracja przed-rudna na samym dole).

**Strefowanie (od centrum/głębi ku dystalnym/płytkim częściom):** propylityczna
(chloryt, epidot, kalcyt, piryt) — dystalna/regionalna → na głębokości: kwarc + chloryt
± adularia (potasowa) → na poziomach pośrednich: kwarc, serycyt, illit (przechodzący ku
górze/dystalnie w smektyt niższotemperaturową) → **płytko: masywna silicyfikacja, sinter
chalcedonowy, wszechobecna alteracja kwaśno-siarczanowa włącznie z kaolinitem i alunitem**.

**Cytat (p. 153):** *"At shallow levels, alteration is characterized by massive
silicification, formation of chalcedonic sinter, and pervasive acid-sulfate alteration,
including alteration to **kaolinite and alunite**."* — ważny niuans: nawet w modelu
"niskosulfidacyjnym" płytka nakładka kwaśno-siarczanowa (parowo-ogrzewana) daje te same
minerały co system wysokosulfidacyjny.

**Minerały wtórne (p. 155):** przed górnictwem: **getyt, jarosit, alunit**, halloysyt,
minerały tlenków manganu; po wietrzeniu górniczym: melanteryt, kopiapit.

**Źródła:**
- Plumlee, G.S., Smith, K.S., Berger, B.R., Foley-Ayuso, N., and Klein, D.P., 1995, Creede, Comstock, and Sado epithermal vein deposits (Models 25b,c,d), *in* du Bray (1995), p. 152–161. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP18.pdf
- Mosier, D.L., and others, 1986a,b,c, Descriptive/grade-tonnage models of Creede/Comstock/Sado epithermal veins, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693.
- Heald, P., Foley, N.K., and Hayba, D.O., 1987, Comparative anatomy of volcanic-hosted epithermal deposits — Acid-sulfate and adularia-sericite types: Economic Geology, v. 82, p. 1–26.
- Berger, B.R., and Eimon, P., 1983 (źródło diagramu zonacji, Fig. 1).
- Plumlee, G.S., and Whitehouse-Veaux, P.H., 1994 (źródło Fig. 2, przekrój Creede district).

---

## 6. Epithermal quartz-alunite Au deposits — wysokosulfidacyjne (Model 25e)

*Plumlee, G.S., et al., in du Bray (1995), Chapter 19 (p. 162–169).*

**Geometria:** koncentryczna, pionowo rozszerzająca się ku górze (upward-flaring) —
komin wokół kanału fluidów, kontynuacja lithocapu porfirowego ku powierzchni.

**Strefowanie (od rdzenia na zewnątrz/w górę):**
- Strefa zaawansowanej argilizacji (pośredni poziom): rdzeń — wyługowana krzemionka
  gąbczasta (vuggy silica), na zewnątrz **kwarc-alunit** (±pirofillit), **kwarc-kaolinit**,
  montmorillonit-illit-smektyt. Piryt obecny we wszystkich strefach.
- Strefa argilityczna (pośredni poziom): montmorillonit-smektyt-illit z pirytem.
- Strefa propylityczna (peryferyjna): **chloryt** ± epidot ± piryt ± **kalcyt**.
- Strefa fylityczna (głęboka): kwarc-serycyt-piryt.

**Zonacja rudna:** głęboko — piryt, chalkopiryt, tennantyt; strefy zaawansowanej
argilizacji/argilityczne — piryt, enargit, kowelin, chalkozyn, natywna siarka, natywne
złoto; peryferyjnie propylityczna — sfaleryt, galena, baryt; płytko — sinter krzemionkowy,
cynober, natywna rtęć(?), natywne złoto, realgar, orpiment.

**Minerały wtórne (p. 164):** supergeniczne — skorodyt, **getyt**, limonit,
**K- i Na-jarosit**, plumbojarosit; z niedawnego wietrzenia — **jarosit** (prawdopodobnie
wzbogacony w hydronium), chalkantyt, brochantyt, melanteryt, alunogen, halotrichit.

To jest model najściślej odpowiadający naszym minerałom PCD — alunit, kaolinit, jarosit
i getyt pojawiają się tu jako nazwane, osobne podstrefy (kwarc-alunit ≠ kwarc-kaolinit),
nie jako jeden zlepek "argilityczny".

**Źródła:**
- Plumlee, G.S., Smith, K.S., Gray, J.E., and Hoover, D.B., 1995, Epithermal quartz-alunite Au deposits (Model 25e), *in* du Bray (1995), p. 162–169. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP19.pdf
- Berger, B.R., 1986, Descriptive model of epithermal quartz-alunite Au, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693, p. 158.
- Stoffregen, R., 1987, Genesis of acid-sulfate alteration and Au-Cu-Ag mineralization at Summitville, Colorado: Economic Geology, v. 82, p. 1575–1591.
- Plumlee, G.S., and others, 1995a (przekrój geologiczny Summitville, źródło Fig. 1 i Fig. 2).

---

## 7. Low-Ti iron oxide Cu-U-Au-REE deposits — typu IOCG (Models 25i, 29b)

*Foose, M.P., and Grauch, V.J.S., in du Bray (1995), Chapter 22 (p. 179–183).*

**Geometria:** koncentryczna/pionowa, głębokie (gorące, magmowe) części systemu vs.
płytsze (chłodniejsze, mieszane) części — patrz Fig. 1 (przekrój Olympic Dam-type).

**Strefowanie (od dołu/głębi ku górze/płycej):**
sodowa (magnetyt + albit ± aktynolit ± apatyt ± chloryt) → potasowa (magnetyt ± hematyt +
apatyt + skaleń potasowy ± serycyt ± albit ± chloryt ± biotyt ± epidot ± węglan ± baryt) →
sercytowa (hematyt + serycyt ± węglan ± baryt ± fluoryt).

**Cytat (p. 179):** *"Magnetite deposition and sodium-rich alteration zones predominate
in the deeper (hotter) parts of these systems, whereas **hematite**, copper-sulfide
minerals, and potassium-rich alteration are more prevalent in their shallower parts."*

**Zonacja rudna:** głęboko — magnetyt, apatyt, mniej chalkopirytu/pirytu; płytko —
**hematyt**, magnetyt, minerały siarczków miedzi, monacyt, uraninit, pitchblenda.

**Źródła:**
- Foose, M.P., and Grauch, V.J.S., 1995, Low-Ti iron oxide Cu-U-Au-REE deposits (Models 25i, 29b), *in* du Bray (1995), p. 179–183. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP22.pdf
- Cox, D.P., 1986a,b, Descriptive models of volcanic-hosted magnetite / Olympic Dam Cu-U-Au, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693, p. 172, 200.
- Hitzman, M.W., Oreskes, N., and Einaudi, M.T., 1992, Geological characteristics and tectonic setting of Proterozoic iron oxide (Cu-U-Au-REE) deposits: Precambrian Research, v. 58, p. 241–287. (uzasadnienie połączenia dwóch podtypów w jeden model; źródło Fig. 1)
- Gow, P.A., Wall, V.J., Oliver, N.S., and Valenta, R.K., 1994, Proterozoic iron oxide (Cu-U-Au-REE) deposits — Further evidence of hydrothermal origins: Geology, v. 22, p. 633–636.

---

## 8. Sediment-hosted Au deposits — typu Carlin (Model 26a)

*Hofstra, A.H., et al., in du Bray (1995), Chapter 23 (p. 184–192).*

**Geometria:** dyseminowana w skałach węglanowych, strefowanie względem reaktywności
skały (dekalcyfikacja/dedolomityzacja), nie wokół pojedynczej intruzji punktowej.

**Strefowanie (od rdzenia refraktorycznej rudy na zewnątrz):**
strefa wewnętrzna — zdekalcyfikowana, ±zdedolomityzowana, ±zargilityzowana,
±skrzemieniowana, zsulfidyzowana; lokalnie realgar/orpiment → strefa pośrednia — dolomit
stabilny, mika 2M1 stabilna, częściowo zdekalcyfikowana, zsulfidyzowana → strefa
zewnętrzna — kalcyt stabilny, zsulfidyzowana.

**Zonacja rudna:** ruda refraktoryczna wewnętrzna — kwarc, ±dolomit, mika, piryt,
markasyt, orpiment, realgar, **kaolinit**, illit/smektyt; ruda utleniona (oxide ore) —
kalcyt, dolomit, kwarc, mika, **limonit/getyt/hematyt**, **kaolinit**, illit/smektyt,
relikty pirytu.

**Minerały wtórne (p. 186):** trawertyn, **getyt**, limonit, **hematyt**, **alunit**,
**kaolinit**, stibikonit, skorodyt, gips.

**Źródła:**
- Hofstra, A.H., Leventhal, J.S., Grimes, D.J., and Heran, W.D., 1995, Sediment-hosted Au deposits (Model 26a), *in* du Bray (1995), p. 184–192. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP23.pdf
- Berger, B.R., 1986, Descriptive model of sediment-hosted Au, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693.
- Bagby, W.C., and Berger, B.R., 1985, Geologic characteristics of sediment-hosted, disseminated precious-metal deposits in the western United States: Reviews in Economic Geology, v. 2, p. 169–202.
- Hofstra, A.H., and others, 1991; Arehart, G.B., and others, 1993a,b (geneza rudy refraktorycznej, izotopy siarki).

---

## 9. Low sulfide Au quartz veins — orogeniczne (mezotermalne) (Model 36a)

*Goldfarb, R.J., et al., in du Bray (1995), Chapter 34 (p. 261–267).*

**Geometria: LINIOWA, nie koncentryczna** — kontrolowana strukturalnie wzdłuż stref
ścinania/uskoków, z zonacją pionową wzdłuż struktury (Fig. 1: od przejścia
kruchy-plastyczny blisko intruzji, w górę do paleopowierzchni). To jedyny model w tym
katalogu, gdzie geometria "koncentryczna wokół punktu" w ogóle nie ma zastosowania —
generator dla tego typu potrzebowałby szkieletu wzdłuż linii/krzywej (uskok), nie wokół
centrum.

**Strefowanie:** otoczki alteracyjne słabo rozwinięte w skałach metaosadowych, ale szerokie
i wyraźne w skałach felzytowych i mafitowych. Piryt/arsenopiryt rozproszone w szerokich
otoczkach. Serycyt blisko żył ze złotem; **chloryt-epidot propylityczny** dystalnie od
żył. Talk, chloryt, fuchsyt w skałach ultramaficznych; albit w skałach granitoidowych.
Pionowo wzdłuż struktury: As, W, Fe głębiej → Sb, As, ±Fe pośrednio → Hg najpłycej
(blisko paleopowierzchni).

**Minerały wtórne:** rzadkie; okazjonalnie arsenopiryt zwietrzały do skorodytu, niewielki
limonit.

**Źródła:**
- Goldfarb, R.J., Berger, B.R., Klein, T.L., Pickthorn, W.J., and Klein, D.P., 1995, Low sulfide Au quartz veins (Model 36a), *in* du Bray (1995), p. 261–267. https://pubs.usgs.gov/of/1995/ofr-95-0831/CHAP34.pdf
- Berger, B.R., 1986, Descriptive model of low-sulfide Au-quartz veins, *in* Cox, D.P., and Singer, D.A., eds., Mineral deposit models: U.S. Geological Survey Bulletin 1693, p. 239.
- Groves, D.I., Barley, M.E., and Ho, S.E., 1989, Nature, genesis, and tectonic setting of mesothermal gold mineralization in the Yilgarn block, Western Australia, *in* Keays, R.R., and others, eds., The geology of gold deposits: Economic Geology Monograph 6, p. 71–85.
- Kerrich, R., and Wyman, D., 1990, Geodynamic setting of mesothermal gold deposits — An association with accretionary regimes: Geology, v. 18, p. 882–885. (źródło modelu geometrii liniowej/strukturalnej, Fig. 1)

---

## Tabela krzyżowa — nasze 7 minerałów PCD vs. modele złóż

| Minerał | Występuje w | Rola |
|---|---|---|
| **Alunit** | Porfir (górna strefa wysokoglinowa), LS epitermalne (płytka nakładka kwaśno-siarczanowa), HS epitermalne (strefa zaawansowanej argilizacji, kwarc-alunit + supergeniczny), Carlin-type (supergeniczny) | Wskaźnik zaawansowanej argilizacji / nakładki lithocap |
| **Kaolinit** | Porfir (górna strefa), HS epitermalne (osobna podstrefa kwarc-kaolinit), LS epitermalne (płytka nakładka), Carlin-type (ruda refraktoryczna + utleniona + supergeniczny) | Wskaźnik argilizacji, szeroko rozpowszechniony |
| **Jarosit** | VMS (wtórny, gossan), LS epitermalne (wtórny), HS epitermalne (supergeniczny, dominujący) | Prawie zawsze wtórny/supergeniczny, nie pierwotny |
| **Getyt** | Fe-skarn (wietrzenie magnetytu), VMS (gossan), LS+HS epitermalne (supergeniczny), Carlin-type (ruda utleniona + supergeniczny) | Produkt utlenienia siarczków/tlenków Fe — najbardziej uniwersalny wskaźnik wietrzenia |
| **Hematyt** | Fe-skarn (skapolitowo-albitowy, ruda + wtórny), IOCG (płytka ruda), Carlin-type (ruda utleniona) | Częściej pierwotny/ruda niż czysto wtórny (w przeciwieństwie do getytu/jarositu) |
| **Chloryt** | Porfir (propylityczna), skarny Cu/Au/Zn-Pb i Fe (retrogradacja), VMS (dominująca alteracja footwall!), LS+HS epitermalne (propylityczna), IOCG (sodowa/potasowa), orogeniczne Au (propylityczna dystalna) | Najbardziej uniwersalny minerał — obecny niemal wszędzie jako propylityczny/dystalny |
| **Kalcyt** | Porfir (propylityczna), Fe-skarn magnezowy (prograde/ruda), LS epitermalne (rodochrozyt/kalcyt manganonośny, bardzo obfity), HS epitermalne (propylityczna), Carlin-type (zewnętrzna/utleniona), orogeniczne Au (alteracja węglanowa) | Powszechny w strefach dystalnych/propylitycznych i jako bufor kwasu |

**Obserwacja praktyczna:** getyt, jarosit i częściowo alunit/kaolinit są w większości
modeli minerałami **wtórnymi/supergenicznymi** (produktami wietrzenia pierwotnych
siarczków), a nie pierwotnymi minerałami hydrotermalnymi — co oznacza, że w generatorze
map alteracji powinny być modelowane jako nakładka zależna od głębokości utlenienia
(patrz Fig. 2 w rozdziale HS epitermalnym, p. 164 — profil głębokości utlenienia), nie
jako statyczna, głęboka strefa współrzędna z resztą zonacji.
