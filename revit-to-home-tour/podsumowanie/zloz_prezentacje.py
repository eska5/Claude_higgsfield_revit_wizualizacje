# -*- coding: utf-8 -*-
"""Build prezentacja.pptx. Run from this folder: python zloz_prezentacje.py"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, 'zdjecia')
W, H = Inches(13.333), Inches(7.5)
INK = RGBColor(0x0E, 0x12, 0x18)
GOLD = RGBColor(0xE4, 0xB5, 0x6A)
WHITE = RGBColor(0xF4, 0xF6, 0xFA)
MUTED = RGBColor(0xB3, 0xBD, 0xCC)

S = [
    ('title', 'Jak w jedno popołudnie powstała strona z modelu',
     ['Snowdon Towers, 13 listopada 2026', 'Od promptu o 16:42 do pierwszej strony około 17:21', 'Druga wersja i publikacja tego samego wieczoru'],
     None, 'Nie mów, że robił to Fable. Slajd 3 tłumaczy, skąd ta nazwa.'),
    ('text', 'Skąd jest ten pokaz',
     ['Z zapisu tego czatu: 356 zdarzeń, od 14:41.',
      'Nie z pamięci i nie z artykułu.',
      'Każda godzina na slajdach jest z tego zapisu.',
      'Sesji, w której Fable wybierał kadry, w tym zapisie nie ma.'],
     None, 'Jak ktoś pyta o Fable, zostań przy slajdzie 3.'),
    ('text', 'Czym jest Fable 5.2',
     ['To model Claude’a, którym zrobiono artykuł-wzorzec.',
      'Z artykułu wzięto prompt, kolejność i zdjęcia.',
      'Nie wzięto jego decyzji. Tej sesji tu nie ma.',
      'Kadry tej strony wybrał agent tego czatu. Ty je zatwierdziłeś.'],
     None, 'Wątek zaczyna się od szukania „Fable 5.2 Revit Higgsfield”. To było szukanie artykułu, nie uruchomienie Fable.'),
    ('text', 'Oś czasu jednego dnia',
     ['14:41–16:40: przewodniki, który plik, połączenie z Revitem.',
      '16:42: prompt „przeczytaj model”.',
      '16:52 i 16:53: dwa razy A. Zestaw kamer, potem zmierzch.',
      '17:21 pierwsza strona. 17:28 odrzucenie obrysu. 17:47 commit.',
      'Wieczór: druga wersja. 20:53 publikacja.'],
     None, 'Od 16:42 do 17:21 jest około 40 minut. Do commita v1 około godzina. v2 nie ma jednej godziny startu w zapisie.'),
    ('text', '16:42, co kazał prompt',
     ['Najpierw przeczytaj: poziomy, lokale, kamery. Potem pytaj po jednym.',
      'Pracuj na kopiach. Nie zapisuj modelu.',
      'Zrób cięcie z góry w dół, piętro po piętrze.',
      'Obraz ma zostawić kamerę i budynek. Liczby mają być z modelu.'],
     None, 'To jest ten sam prompt, który jest w guide.md. Wklejony o 16:42.'),
    ('text', 'Co było w pliku o 16:52',
     ['18 poziomów, od parkingu po attykę.',
      '21 mieszkań na L2–L5. Hol 106 nie jest mieszkaniem.',
      '50 widoków 3D, 366 widoków w ogóle.',
      'Widoki HT Aerial, Street, Rooftop, Loft 405 i Cut L2–L5 już były.',
      'Wątek nie ma kroku, w którym ktoś je dopiero wstawiał.'],
     None, 'Nie przypisuj tych kamer Fable’owi. O 16:52 były już na liście.'),
    ('text', 'Decyzja 1. Które kadry',
     ['A, zestaw spaceru: z góry, ulica, dach, loft 405. Rekomendowany.',
      'B, róg od rzeki. Chowa ulicę.',
      'C, życie parteru: hol, taras, lokal 302. Mało całego budynku.',
      '16:52, odpowiedź: A.'],
     None, 'A wygrało, bo pokazuje bryłę i jedno wnętrze. B i C zostały opisane, nie użyte.'),
    ('text', 'Decyzja 2. Jaki wygląd',
     ['Trzy karty wyglądu, po eksporcie kadrów.',
      '16:53, drugie A: zmierzch, ciemne tło, ciepłe światło.',
      'Cięcia miały iść z kopii widoków HT Cut.',
      'Model bez zapisu.'],
     None, 'Dwa A pod rząd. Najpierw kadry, potem wygląd. Tak kazał prompt.'),
    ('text', 'Decyzja 3. Dziesięć kredytów',
     ['Pełny zestaw zdjęć i filmów się nie mieścił.',
      'A: cztery zdjęcia zmierzchu, cięcia zostają z Revita. 4 kredyty.',
      'B: jedno lepsze zdjęcie i jedna pętla. 9,5. Reszta surowa.',
      'C: zero kredytów, strona tylko z eksportów.'],
     None, 'To było pytanie o 17:01, zanim cokolwiek wydano.'),
    ('text', '„Weź najlepszą ofertę”',
     ['Nie poszło A z cennika za 4 kredyty.',
      'Cztery zdjęcia modelem GPT Image 2, około 0,5 kredytu sztuka.',
      'Wydane 2, zostało 8.',
      'Cięcia na stronie v1 to PNG z Revita, bez filmu. Dlatego.'],
     None, 'Tańszy model dał cztery kadry zamiast jednego drogiego. Zostało na dobicie.'),
    ('text', '17:21, pierwsza strona',
     ['Folder run/sales-page.',
      'Najazd na piętro pokazywał liczbę mieszkań.',
      'Lista 21 lokali, stopy i metry.',
      'Cięcie L5 do L2, dach, ulica, loft 405.',
      'Obrys i pinezki nie były jeszcze z geometrii.'],
     None, 'To jest wersja, którą potem oceniono jako zły obrys.'),
    ('image', 'Kadr, który został',
     ['To ujęcie jest z drugiej wersji, ta sama kamera.',
      'W pierwszej wersji obraz przyciął kadr do 16:9.',
      'Procenty policzone wcześniej przestały pasować.'],
     'zmierzch.jpg', 'Pokaż, że bryła jest z kamery, a światło doszło później.'),
    ('text', '17:28, ocena',
     ['Na wzorcu są jadące samochody i przejścia między ujęciami.',
      'Obrys budynku został odrzucony.',
      'Saldo obrazów było już 0.',
      'Ostatnie 8 kredytów poszło na ostrzejsze zdjęcie, cięcia i klip 3 s.'],
     None, 'Klip 3 s kończył się na dachu, więc obrys i tak nie mógł na nim leżeć.'),
    ('text', 'Cztery powody, dla których obrys kłamał',
     ['Maska koloru dała gruby kontur, nie płytę stropu.',
      'Obraz przekadrował eksport. Ślad z Revita został przy starym kadrze.',
      'Strona rozciągała obraz, więc procent siadał obok.',
      'Pinezki były procentami wpisanymi na oko.'],
     None, 'To jest spisane przy commicie o 17:47. Wcześniejsza wiadomość mówiła, że obrys jest naprawiony. Nie był.'),
    ('text', '17:47, co przyznano przy commicie',
     ['Wielokąty są ręczne. Automatyczne śledzenie padło.',
      'Samochodów w klipie nie sprawdzono.',
      'Filmu-wzoru nie dało się otworzyć na tej maszynie.',
      'Opis loftu 405 przepisano z artykułu, nie z modelu.',
      '„Wejdź” dla lokalu innego niż 405 pokazywało cięcie piętra.'],
     None, 'Commit 5063cdf. Surowe maski, około 255 MB, nie weszły do gita.'),
    ('text', 'Dlaczego powstała druga wersja',
     ['Po doładowaniu, w osobnym folderze sales-page-v2.',
      'Pierwsza została, żeby było co porównać.',
      'Nowe kamery nazywają się HT2 i są kopiami.',
      'Tym razem najpierw geometria, potem obraz.'],
     None, 'Godziny startu v2 nie ma w jednym zdaniu zapisu. Było to po 17:47, tego samego wieczoru.'),
    ('text', 'Dlaczego budynek wie, gdzie jest',
     ['To nie jest GPS i nie jest rozpoznawanie zdjęcia.',
      'Kamera ma oko, trzy osie i prostokąt kadru. W stopach.',
      'Pomieszczenie ma punkt. Też w stopach.',
      'Rzut tego punktu na prostokąt daje procent szerokości i wysokości.',
      'Strona rysuje pinezkę w tym procencie, na tym samym 16:9.'],
     None, 'Jak obraz ruszy kadr, procent zostaje, a budynek na zdjęciu już nie. Stąd cały filtr filmów.'),
    ('text', 'Skrypt, który to liczy: proj.py',
     ['Odejmuje oko kamery od punktu pomieszczenia.',
      'Rozkłada różnicę na prawo, górę i przód.',
      'Przez podobieństwo trójkątów kładzie punkt na kadr.',
      'homes() bierze lokale mieszkalne i wyrzuca numer 106.',
      '106 to hol. Inaczej dostałby pinezkę jak mieszkanie.'],
     None, 'Jeden wzór dla pinezek, obrysów i podpisów na ulicy.'),
    ('text', 'Ulica: 0,1 stopy',
     ['Pierwsze punkty kawiarni i sklepów wypadły poza obraz.',
      'Dalsza ścianka crop boxa nie jest płaszczyzną kadru.',
      'U tej kamery prostokąt leży 0,1 stopy przed okiem.',
      'Po wstawieniu 0,1 podpisy spadły na parter.',
      'Metraż przy nazwie jest z pomieszczenia. Szyld nie jest.'],
     None, 'build_site_data.py robi to tylko dla hotspotów ulicy i dachu.'),
    ('image', 'Obrys policzony, nie narysowany',
     ['Każdy kolor to kondygnacja widziana tą kamerą.',
      'Wyższe zasłania niższe.',
      'Taras zostaje na swoim stropie.',
      'Ogród na dachu jest nakrywką.'],
     'obrysy.jpg', 'build_overlays.py. Wcześniejsze malowanie od góry zostawiało L3 na dachu.'),
    ('text', 'Dwie kamery w lokalu: pick_room_cams.py',
     ['Surowiec to promienie widoczności, rays_L2 do rays_L5.',
      'Skrypt wybiera dwa punkty, z których widać najwięcej.',
      'Zapis room_cams.json. Pole side jest z położenia punktu.',
      '„Strona rzeki” nie jest parametrem modelu.',
      '42 widoki. Ręczne ustawianie powtórzyłoby błąd dachu.'],
     None, 'Błąd dachu: opis prosił o rzekę, a kamera patrzy w ulicę.'),
    ('text', 'Dlaczego ten film, a nie droższy',
     ['Kling 4.0 zostawia pierwszą klatkę.',
      'Skala około 0,997. Przesunięcie rzędu 2 pikseli na 10 s.',
      'Seedance 2.5 przesunął scenę o kilkadziesiąt pikseli.',
      'Wyglądał lepiej i odpadł, bo obrys jest przyklejony do pikseli.'],
     None, 'Mierzył to align_check.py, na klatce wobec zdjęcia wzorcowego.'),
    ('text', 'Skrypty, które pilnują kadru',
     ['align_check.py: skala i przesunięcie filmu wobec zdjęcia.',
      'vid_check.py: czy na ulicy w ogóle są samochody.',
      'ref_frames.py i ref_site.py: klatki odniesienia przed wydatkiem.',
      'check_overlay.py: wielokąt narysowany na zdjęciu.',
      'check_proj.py: próbny rzut, zanim liczy się cały obrys.'],
     None, 'Przy v1 zdania „są samochody” nikt nie sprawdził. Te skrypty są po to, żeby tego nie powtórzyć.'),
    ('image', 'Dach patrzy w ulicę',
     ['Na zdjęciu jest poprawka: za altaną miasto.',
      'Pierwsza wersja miała rzekę, bo opis o nią prosił.',
      'W modelu rzeka jest po przeciwnej stronie kamery.',
      'Zdjęcie i dwa filmy zrobiono drugi raz.'],
     'dach.jpg', 'Stare pliki zostały jako rooftop-old. Strona ich nie używa.'),
    ('text', 'Skrypty pierwszej wersji',
     ['export_previews.py: PNG z nazwanych widoków.',
      'trace_floors.py i trace_floors2.py: maska koloru. Padły.',
      'build_outlines.py i floor-hulls.json: wielokąty wpisane ręcznie.',
      'choices.md: zapis dwóch A. Zostało w nim stare „8 kredytów”.'],
     None, 'choices.md nie poprawiono przy commicie, bo diff był już obejrzany. Saldo było 0.'),
    ('text', 'Skrypty drugiej wersji, dane',
     ['rooms.json: numer, nazwa, metraż, poziom, punkt.',
      'cams_ht2.json: oko, osie, kadr.',
      'overlays.json: wynik build_overlays.py, w procentach.',
      'jobs.json: nazwa ujęcia i identyfikator zlecenia. Poza gitem.',
      'dl.py: ściąga wynik po skrócie czasu. Ma identyfikator konta, też poza gitem.'],
     None, 'jobs.json i dl.py zostały lokalnie, bo w adresie jest konto.'),
    ('text', 'Skrypty drugiej wersji, obrazy',
     ['hf_upload.py: wysyła PNG, zapisuje media_ids.json.',
      'hf_get.py: ściąga wynik i robi podgląd.',
      'sheet.py i preview.py: kontaktówki, kilka ujęć na jednym JPG.',
      'Higgsfield nie czyta dysku. Każde zlecenie szło ręcznie, po 12.'],
     None, 'tour_status.py nie woła Higgsfield. Tylko mówi, czego brakuje.'),
    ('text', 'Składanie strony',
     ['build_site_data.py pisze data.js. Nie edytować ręcznie.',
      'Suwak: klatka filmu najbliższa zdjęciu danej godziny.',
      'Świt 0 s, południe 2,6 s, złota godzina 9 s, zmierzch 10 s, noc 12 s.',
      'build_site_assets.py: JPEG, pętla zlepiona z początkiem, cofnięcie to ten sam film wstecz.'],
     None, 'Cofnięcie nie jest nowym, płatnym filmem.'),
    ('text', 'app.js, czyli ruch na stronie',
     ['Graf: z góry na piętro, piętro na piętro, z góry na dach i ulicę.',
      'Dłuższa droga leci 1,4 razy szybciej.',
      'Następny klip ładuje się, zanim skończy się bieżący.',
      'Schowana karta pauzuje film. Skrypt go wznawia.',
      'Film poklatkowy idzie do pamięci, bo przewijanie po sieci skakało.'],
     None, 'Te trzy ostatnie wyszły przy teście, nie przy rysowaniu.'),
    ('image', 'Plan jest przecięciem z Revita',
     ['Poziom 4, osiem lokali.',
      'Numery i metraż z pomieszczeń.',
      'Meble na planie są dopowiedziane.',
      'Obrys lokalu jest z jego geometrii, przez tę kamerę.'],
     'pietro-4.jpg', 'Największy lokal na tym piętrze to 407, około 1146 stóp.'),
    ('image', 'Wnętrze ma granicę',
     ['Dwa ujęcia na lokal, z dwóch kamer HT2.',
      'Wlot wchodzi na dobre piętro.',
      'Nie da się pokazać, że to dokładnie ten numer.',
      'Meble są ilustracją. Na stronie jest o tym zdanie.'],
     'wnetrze.jpg', 'Styl zależy od piętra: 2 ciepło, 3 mid-century, 4 loft, 5 współcześnie.'),
    ('image', 'Pięć pór, jedna kamera',
     ['Świt, południe, złota godzina, zmierzch, noc.',
      'Jeden zestaw procentów pasuje do wszystkich.',
      'Suwak jedzie po filmie 12 s, potem zostawia pętlę.',
      'Złota godzina i zmierzch wyszły bardzo blisko.'],
     'poludnie.jpg', 'Następnym razem te dwie godziny trzeba rozsunąć już w opisie światła.'),
    ('text', 'Jak to sprawdzano',
     ['serve.py na porcie 8137. Zwykły serwer Pythona nie umie zakresów.',
      'Bez zakresów suwak i pętla filmu nie działają.',
      'W przeglądarce: piętro 4, lokal 407, drugie ujęcie, ulica, dach, południe.',
      'Formularz odrzuca puste pole i zły e-mail. Nic nie wysyła.',
      'Safari, Firefox i prawdziwy telefon nie były otwierane.'],
     None, 'Na żywym adresie przejście z 407 na dach odegrało trzy klipy.'),
    ('text', 'Publikacja, dwie próby',
     ['20:36 pierwsza akcja pada: Pages nie jest włączone.',
      'Repozytorium było prywatne. Darmowe Pages chce publicznego.',
      'Po włączeniu źródła GitHub Actions, 20:53, druga próba przechodzi.',
      'Publikowany jest tylko folder sales-page-v2.',
      'Adres: eska5.github.io/Claude_higgsfield_revit_wizualizacje'],
     None, 'Skoro repozytorium jest publiczne, widać też przewodniki i stronę v1.'),
    ('text', 'Czego nie ma w gicie',
     ['Surowe rendery, około 2,5 GB, w v2-work/hf.',
      'jobs.json, dl.py, media_ids.json.',
      'Powód: waga i identyfikator konta w adresie pobierania.',
      'W gicie jest strona, około 205 MB, i skrypty, które składają dane.'],
     None, 'Nie robić git add wszystkiego. Surowy render wejdzie na stałe.'),
    ('text', 'Koszt',
     ['v1: około 2 kredyty, potem ostatnie 8. Saldo 0.',
      'v2: około 1900 z 3000, suma zleceń, nie wyciąg z konta.',
      'Najdroższe były filmy wnętrz i pętle.',
      'Zdjęcia szły przed filmami, bo zły kadr unieważnia klip.',
      'Salda konta nie odczytano.'],
     None, 'Następny budynek nie wyjdzie w tej samej kwocie. Zależy od liczby lokali.'),
    ('text', 'Co na stronie jest z modelu',
     ['Numer, typ z nazwy pomieszczenia, metraż, poziom.',
      'Obrys piętra i obrys lokalu.',
      'Pinezka w punkcie pomieszczenia.',
      'Metraż ogrodu, altany, kawiarni, sklepów, parku i holu.',
      'Kadr kamery. Światło już nie.'],
     None, 'To da się sprawdzić w zestawieniu pomieszczeń i we właściwościach widoku.'),
    ('text', 'Czego strona nie wie',
     ['Ceny i tego, czy lokal jest wolny.',
      'Umeblowania. Szyldów.',
      'Prawdziwego widoku z okna.',
      'Czy wlot trafił w ten numer, czy w sąsiedni na piętrze.',
      'Strony rzeki, dopóki nie ma parametru.'],
     None, 'Parametr przy pomieszczeniu wyłącza zgadywanie. Reszta zostaje ilustracją, jeśli tak zdecydujecie.'),
    ('text', 'Żeby następnym razem nie odkrywać tego samo',
     ['next-project.md: kolejność, łącznie z 0,1 stopy i kierunkiem dachu.',
      'python tour_status.py: lista braków.',
      'Na ten budynek: 11/11 kadrów, 21/21 klipów, 105/105 plików mieszkań.',
      'tour_status.py --build składa obrysy, data.js i pliki strony.',
      'Generowania obrazów nie uruchamia. To dalej kosztuje.'],
     None, 'Skrypt jest dla następnego budynku. Tego nie przelicza od zera.'),
    ('text', 'Pytania',
     ['Które widoki HT i HT2 skasować? Model nie był zapisywany.',
      'Czy lokal dostaje parametr strony, status i cenę?',
      'Czy wnętrze na stronie ma być puste, czy umeblowane w modelu?',
      'Który budynek jest drugi?'],
     None, 'Zamknięcie bez zapisu zabiera widoki HT i HT2. Geometrii budynku nie ruszano.'),
]
SLIDES = S


def fill(shape, text, size, color, bold=False):
    shape.word_wrap = True
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = 'Calibri'
    return tf


def add_lines(tf, lines, size, color, space=8):
    for line in lines:
        p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_before = Pt(space)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = 'Calibri'


def shade(slide, color):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.line.fill.background()
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    sp = bg._element
    sp.getparent().remove(sp)
    slide.shapes._spTree.insert(2, sp)


def bar(slide):
    mark = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.12), H)
    mark.line.fill.background()
    mark.fill.solid()
    mark.fill.fore_color.rgb = GOLD


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build():
    if len(SLIDES) != 40:
        raise SystemExit('slajdów jest %d, ma być 40' % len(SLIDES))
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = 'Jak powstała strona ze Snowdon Towers'
    blank = prs.slide_layouts[6]
    for index, (kind, title, lines, image, note) in enumerate(SLIDES, start=1):
        slide = prs.slides.add_slide(blank)
        shade(slide, INK)
        bar(slide)
        num = slide.shapes.add_textbox(Inches(12.3), Inches(7.05), Inches(0.8), Inches(0.32))
        fill(num, str(index), 12, MUTED)
        if kind == 'title':
            box = slide.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(11.5), Inches(2.4))
            tf = fill(box, title, 36, WHITE, bold=True)
            add_lines(tf, lines, 20, GOLD, space=10)
        elif kind == 'image':
            box = slide.shapes.add_textbox(Inches(0.45), Inches(0.28), Inches(5.4), Inches(1.5))
            tf = fill(box, title, 24, WHITE, bold=True)
            body = slide.shapes.add_textbox(Inches(0.45), Inches(1.9), Inches(5.3), Inches(4.8))
            tf = fill(body, lines[0], 16, MUTED)
            add_lines(tf, lines[1:], 16, MUTED, space=10)
            slide.shapes.add_picture(os.path.join(IMG, image), Inches(5.9), Inches(0.85), height=Inches(5.6))
        else:
            box = slide.shapes.add_textbox(Inches(0.5), Inches(0.32), Inches(12.2), Inches(1.5))
            fill(box, title, 28, WHITE, bold=True)
            body = slide.shapes.add_textbox(Inches(0.5), Inches(1.9), Inches(12.2), Inches(4.8))
            tf = fill(body, lines[0], 20, MUTED)
            add_lines(tf, lines[1:], 20, MUTED, space=12)
        notes(slide, note)
    out = os.path.join(HERE, 'prezentacja.pptx')
    prs.save(out)
    print(out, len(SLIDES))


if __name__ == '__main__':
    build()
