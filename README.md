# Kodi doplněk pro TALK.cz (dříve TALKTV.cz, STANDASHOW)

Napsáno téměř výhradně s pomocí Claude.AI.

## Přihlášení

Bohužel, talktv.cz používá na přihlašovací stránce reCaptchu přes kterou se mi nepodařilo projít.

V nastavení je tak záložní varianta se zkopírováním session cookie, což je trochu nepohodlné, ale nevadilo by, kdyby ta cookie neměla platnost 1 měsíc, takže se to bude muset pravidelně opakovat.

## Co funguje

* **Funkce**
    * Přihlášení přes PHPSESSID (cookie vykopírované z prohlížeče)

* **Menu**
    * **Hledání** - To zdá se funguje dobře. (Ve výsledcích hledání nejsou popisky epizod, jen název a délka, proto, nejsou ani v Kodi)
    * **Poslední videa** - Také zdá se, že fungují dobře.
    * **Tvůrci** - V podmenu jsou všechny aktuální pořady od STANDASHOW po DESIGN TALK. Zde fungují i popisy epizod a data přidání.
    * **Archiv** - V podmenu jsou seznamy videí (IRL, HODNOCENÍ HOSTŮ, VOLBY, ...) a archivované pořady (JARDA VS NAOMI)

## Co nefunguje

* **Funkce**
    * Přihlášení přes talktv.cz jméno a heslo - reCaptcha
    * Přihlášení přes Patreon

* **Menu**
    * **Populární videa** - Jako fungují, ale ```<div id='homePopular'>``` v pluginu dostává jiné HTML než je na webu.

## Co přidat

* Živé streamy?
* Skok na čas, kdy skončila YT část videa - by bylo fajn, ale netuším jak.
* V **Poslední videa** by bylo hezké přidat před název epizody ještě název pořadu, <br>ale i přes to, že se popis dohledává na stránce videa, tak ani tam nelze určit název pořadu. Ani z URL.
* Cachování?
