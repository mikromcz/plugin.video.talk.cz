# Kodi doplněk pro TALK.cz (dříve TALKTV.cz, STANDASHOW)

Napsáno téměř výhradně s pomocí Claude.AI.

## Přihlášení

Bohužel, talktv.cz používá na přihlašovací stránce reCaptchu přes kterou se mi zatím nepodařilo projít.

V nastavení je tak záložní varianta se zkopírováním session cookie, což je trochu nepohodlné, protože ta cookie má platnost 1 měsíc, takže se to bude muset pravidelně opakovat.

## Co funguje

* **Funkce**
    * Přihlášení přes PHPSESSID (cookie vykopírované z prohlížeče)
    * Kešování popisů epizod a datumů - menší zátěž pro server Talku, značné zrychlení doplňku
    * Skok na čas, kdy skončila YouTube část videa (Tak trochu. Jen spustí video od času nastaveného v nastavení - průměrná délka YouTube části je cca 22 minut)

* **Menu**
    * **Hledání**
    * **Poslední videa**
    * **Populární videa**
    * **Nejlepší videa** - Tahle kategorie ani není na webu 😀.
    * **Pokračovat v přehrávání** - Neaktualizuje se při sledování přes Kodi 😌. (Zatím? 🤔)
    * **Tvůrci** - V podmenu jsou všechny aktuální pořady od STANDASHOW po DESIGN TALK.
    * **Archiv** - V podmenu jsou seznamy videí (IRL, HODNOCENÍ HOSTŮ, VOLBY, ...) a archivované pořady (JARDA VS. NAOMI 🪦)

## Co nefunguje

* **Funkce**
    * Přihlášení přes talktv.cz jméno a heslo
    * Přihlášení přes Patreon

## Co přidat

* Živé streamy?
* V **Poslední, Populární, Nejlepší videa** by bylo hezké přidat před název epizody ještě název pořadu. Bohužel jsem zatím neobjevil způsob, jak by se ho dalo jednoduše získat.
    * To by pak šlo dát do kontextového menu "Přejít na pořad"
* Přidat logo TALKu, nebo přímo pořadu k titulku videa při přehrávání. Ale to už je frajeřinka.
