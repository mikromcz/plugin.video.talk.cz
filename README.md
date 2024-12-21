# Kodi doplněk pro TALK.cz (dříve TALKTV.cz, STANDASHOW)

Napsáno téměř výhradně s pomocí Claude.AI.

## Přihlášení

Bohužel, talktv.cz používá na přihlašovací stránce reCaptchu přes kterou se mi nepodařilo projít.

V nastavení je tak záložní varianta se zkopírováním session cookie, což je trochu nepohodlné, ale nevadilo by, kdyby ta cookie neměla platnost 1 měsíc, takže se to bude muset pravidelně opakovat.

## Co funguje

* **Funkce**
    * Přihlášení přes PHPSESSID (cookie vykopírované z prohlížeče)

* **Menu**
    * **Hledání** - To zdá se funguje dobře. (Ve výsledcích hledání nejsou popisky epizod, jen název a délka.)
    * **Poslední videa** - Scrapuje se z webu.
    * **Populární videa** - Tahají se přes API 😉
    * **Nejlepší videa** - Tahají se přes API 😉. Tahle kategorie není ani na webu 😀.
    * **Pokračovat v přehrávání** - Tahají se přes API 😉. Neaktualizuje se ale při sledování přes Kodi 😌.
    * **Tvůrci** - V podmenu jsou všechny aktuální pořady od STANDASHOW po DESIGN TALK.
    * **Archiv** - V podmenu jsou seznamy videí (IRL, HODNOCENÍ HOSTŮ, VOLBY, ...) a archivované pořady (JARDA VS NAOMI)

## Co nefunguje

* **Funkce**
    * Přihlášení přes talktv.cz jméno a heslo - reCaptcha
    * Přihlášení přes Patreon

## Co přidat

* Živé streamy?
* Skok na čas, kdy skončila YT část videa - by bylo fajn, ale netuším jak.
* V **Poslední videa** by bylo hezké přidat před název epizody ještě název pořadu, <br>ale i přes to, že se popis dohledává na stránce videa, tak ani tam nelze určit název pořadu. Ani z URL.
    * To by pak šlo dát do kontextového menu "Přejít na pořad"
* Kešovat data pořadů
* Přidat logo TALKu, nebo přímo pořadu k titulku videa při přehrávání. Ale to už je frajeřinka.
