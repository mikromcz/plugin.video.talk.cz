import sys
import xbmcaddon

_URL = sys.argv[0]  # Base URL of the addon
_HANDLE = int(sys.argv[1])  # Handle for the Kodi plugin instance
_ADDON = xbmcaddon.Addon()  # Instance of the addon
ADDON_ID = _ADDON.getAddonInfo('id')  # ID of the addon

# Main menu categories
MENU_CATEGORIES = [
    {
        'name': '[COLOR limegreen]TALKNEWS[/COLOR]',
        'url': 'talknews',
        'description': 'Novinky na [COLOR limegreen]TALK[/COLOR]u.\n\nNadcházející streamy, nové pořady a všechny důležité informace.',
        'image': 'talknews.png'
    },
    {
        'name': 'Poslední videa',
        'url': 'https://www.talktv.cz/videa',
        'description': 'Nejnovější videa na [COLOR limegreen]TALK[/COLOR]u.',
        'image': 'latest.png'
    },
    {
        'name': 'Populární videa',
        'url': 'popular',
        'description': 'Trendující videa na [COLOR limegreen]TALK[/COLOR]u.',
        'image': 'popular.png'
    },
    {
        'name': 'Nejlepší videa',
        'url': 'top',
        'description': 'Nejsledovanější videa na [COLOR limegreen]TALK[/COLOR]u.\n\n[COLOR slategrey]Poznámka: Tato kategorie není dostupná ve webovém rozhraní.\nObsahuje 16 "top" videí.[/COLOR]',
        'image': 'top.png'
    },
    {
        'name': 'Pokračovat v přehrávání',
        'url': 'continue',
        'description': 'Rozkoukaná videa na [COLOR limegreen]TALK[/COLOR]u.\n\n[COLOR slategrey]Poznámka: I rozkoukaná v Kodi.[/COLOR]',
        'image': 'continue-watching.png'
    },
    {
        'name': 'Tvůrci',
        'url': 'creators',
        'description': 'Všichni tvůrci na [COLOR limegreen]TALK[/COLOR]u a jejich pořady.\n\n[COLOR limegreen]STANDASHOW[/COLOR]\n[COLOR limegreen]TECH GUYS[/COLOR]\n[COLOR limegreen]JADRNÁ VĚDA[/COLOR]\n[COLOR limegreen]ZA HRANICÍ[/COLOR]\n[COLOR limegreen]MOVIE WITCHES[/COLOR]\n[COLOR limegreen]DESIGN TALK[/COLOR]',
        'image': 'creators.png'
    },
    {
        'name': 'Seznamy videí & Archiv',
        'url': 'archive',
        'description': 'Speciální série a archiv pořadů [COLOR limegreen]TALK[/COLOR]u.\n\n[COLOR limegreen]IRL STREAMY[/COLOR]\n[COLOR limegreen]HODNOCENÍ HOSTŮ[/COLOR]\n[COLOR limegreen]JARDA VS. NAOMI[/COLOR]\na další...',
        'image': 'archive.png'
    },
    {
        'name': 'Hledat',
        'url': 'search',
        'description': 'Vyhledávání v obsahu [COLOR limegreen]TALK[/COLOR]u.',
        'image': 'search.png'
    },
    {
        'name': 'Živě',
        'url': 'live',
        'description': '[COLOR limegreen]STANDASHOW[/COLOR] živě!\n\n[COLOR slategrey]Poznámka: Vyžaduje funkční doplněk YouTube.[/COLOR]',
        'image': 'live.png'
    }
]

# Archive categories
ARCHIVE_CATEGORIES = [
    {
        'name': 'STANDASHOW SPECIÁLY',
        'url': 'https://www.talktv.cz/seznam-videi/seznam-hejktqzt',
        'description': 'Minutu po minutě. Den po dni. Důležité události a exkluzívní hosté ve speciálech [COLOR limegreen]STANDASHOW[/COLOR]. Unikátní formát, který kombinuje prvky podcastu, dokumentu a časové reality show.',
        'image': 'archiv-standashow-specialy.jpg'
    },
    {
        'name': 'IRL PROCHÁZKY Z TERÉNU',
        'url': 'https://www.talktv.cz/seznam-videi/irl-prochazky-z-terenu',
        'description': 'Kamera, baťoh, mikrofony, sim karta, power banky, hromadu kabelů... to jsou IRL streamy. Procházky z terénu. Živé vysílání skoro odkukoli. Mix podcastu, dokumentu a reality show.',
        'image': 'archiv-irl-prochazky.jpg'
    },
    {
        'name': 'HODNOCENÍ HOSTŮ',
        'url': 'https://www.talktv.cz/seznam-videi/hodnoceni-hostu',
        'description': 'Nezapomenutelnou atmosféru a komornější povídání, jak na veřejném vysílání. Takový virtuální sraz [COLOR limegreen]STANDASHOW[/COLOR]. Většinou prozradíme spoustu zajímavostí z backstage.',
        'image': 'archiv-hodnoceni-hostu.jpg'
    },
    {
        'name': 'CHARITA',
        'url': 'https://www.talktv.cz/seznam-videi/charita',
        'description': 'Pomáháme. Podcast má být především zábava, ale někde je třeba probrat i vážné téma. A díky skvělé komunitě, která se kolem [COLOR limegreen]STANDASHOW[/COLOR] vytvořila, můžeme pomoct dobré věci.',
        'image': 'archiv-charita.jpg'
    },
    {
        'name': 'PREZIDENTSKÉ VOLBY 2023',
        'url': 'https://www.talktv.cz/seznam-videi/seznam-bxmzs6zw',
        'description': 'Volba prezidenta České republiky 2023. Pozvali jsme všechny kandidáty a takhle to dopadlo...',
        'image': 'archiv-prezidentske-volby-2023.jpg'
    },
    {
        'name': 'NEJMLADŠÍ POLITICI',
        'url': 'https://www.talktv.cz/seznam-videi/nejmladsi-politici',
        'description': 'Pozvali jsme si ty nejmladší politiky ze všech politických stran zastoupených v parlamentu. A tady je výsledek.',
        'image': 'archiv-nejmladsi-politici.jpg'
    },
    {
        'name': 'VOLBY 2021',
        'url': 'https://www.talktv.cz/seznam-videi/volby-2021',
        'description': '8 politických podcastů, více jak 13 hodin materiálu. V každém rozhovoru se probírají kontroverzní, ale také obyčejná lidská témata.',
        'image': 'archiv-volby-2021.jpg'
    },
    {
        'name': 'JARDA VS. NAOMI',
        'url': 'https://www.talktv.cz/jarda-a-naomi',
        'description': 'Herní novinář [COLOR limegreen]Jarda Möwald[/COLOR] a fanynka japonské popkultury [COLOR limegreen]Naomi Adachi[/COLOR]. Diskuse o zajímavostech ze světa her, filmů a seriálů. Celé záznamy pro předplatitele na talktv.cz.',
        'image': 'show-jarda-vs-naomi.jpg'
    },
    {
        'name': 'ZÁKULISÍ TALKU',
        'url': 'https://www.talktv.cz/seznam-videi/zakulisi-talk-tv',
        'description': 'Toto jsme my. Váš/náš :D [COLOR limegreen]TALK[/COLOR]. A toto jsou všechna videa ze zákulisí.',
        'image': 'archiv-zakulisi-talku.jpg'
    },
    {
        'name': 'OSTATNÍ',
        'url': 'https://www.talktv.cz/videa?filter=ostatni',
        'description': 'Kategorie ostatní na [COLOR limegreen]TALK[/COLOR]u.\n\nJaký je [COLOR limegreen]Standa[/COLOR] šéf?\nJaký je vysněný host?\nKteré pivo je nejlepší?\na další...',
        'image': 'archiv-ostatni.jpg'
    }
]

# Creator categories
CREATOR_CATEGORIES = [
    {
        'name': 'STANDASHOW',
        'url': 'https://www.talktv.cz/standashow',
        'description': 'Výstup z vaší názorové bubliny. Politika, společnost, kauzy a Bruntál. Obsahují minimálně jednoho [COLOR limegreen]Standu[/COLOR].',
        'image': 'show-standashow.jpg',
        'coloring': '1',
        'cast': ['Standa Hruška']
    },
    {
        'name': 'TECH GUYS',
        'url': 'https://www.talktv.cz/techguys',
        'description': 'Kde unboxingy končí, my začínáme. Apple, kryptoměny, umělá inteligence a pak zase Apple. Každý týden s [COLOR limegreen]Honzou Březinou[/COLOR], [COLOR limegreen]Kicomem[/COLOR] a [COLOR limegreen]Davidem Grudlem[/COLOR].',
        'image': 'show-tech-guys.jpg',
        'coloring': '6',
        'cast': ['Honza Březina', 'David Grudl', 'Kicom']
    },
    {
        'name': 'JADRNÁ VĚDA',
        'url': 'https://www.talktv.cz/jadrna-veda',
        'description': 'Pořad, který 9 z 10 diváků nepochopí (a ten desátý je [COLOR limegreen]Leoš Kyša[/COLOR], který to moderuje). Diskuse se skutečnými vědci o skutečné vědě. Pyramidy, kvantová fyzika nebo objevování vesmíru.',
        'image': 'show-jadrna-veda.jpg',
        'coloring': '3',
        'cast': ['Leoš Kyša', 'Jelena Lenka Příplatová', 'Kateřina Rohlenová']
    },
    {
        'name': 'ZA HRANICÍ',
        'url': 'https://www.talktv.cz/za-hranici',
        'description': 'Popelář v Londýně, letuška v Kataru nebo podnikatel v Gambii. Češi žijící v zahraničí a cestovatel [COLOR limegreen]Vladimír Váchal[/COLOR], který ví o cestování (skoro) vše. A na zbytek se nebojí zeptat.',
        'image': 'show-za-hranici.jpg',
        'coloring': '4',
        'cast': ['Vladimír Váchal']
    },
    {
        'name': 'MOVIE WITCHES',
        'url': 'https://www.talktv.cz/moviewitches',
        'description': 'Tři holky [COLOR limegreen]Bety[/COLOR] + [COLOR limegreen]Baty[/COLOR] + [COLOR limegreen]Shial[/COLOR] si povídají o filmech, které si to zaslouží. Od vzpomínek přes zajímavosti a shrnutí děje.',
        'image': 'show-movie-witches.jpg',
        'coloring': '7',
        'cast': ['Bety', 'Baty', 'Shial']
    },
    {
        'name': 'DESIGN TALK',
        'url': 'https://www.talktv.cz/design-talk',
        'description': '[COLOR limegreen]Lukáš Veverka[/COLOR] a jeho hosté diskutují o věcech, kterým většina diváků vůbec nevěnuje pozornost. Filmy, grafika, motion design i největší faily v dějinách designu a kinematografie.',
        'image': 'show-design-talk.jpg',
        'coloring': '8',
        'cast': ['Lukáš Veverka']
    }
]