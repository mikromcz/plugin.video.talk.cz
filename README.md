# Kodi doplněk pro TALK.cz (dříve TALKTV.cz, STANDASHOW)

> Napsáno téměř výhradně s pomocí Claude.AI.

Roky jsem byl *čumilem*. Pak jsem se rozhodl stát se platícím členem, asi tři roky platil, ale stále jel v řežimu *čumil* - koukal jsem na streamy, když mě zaujal host a vystačil si s videi na YouTube. No a došlo mi, že platím a nevyužívám čistě proto, že jsem líný opustit Kodi a spustit celou epizodu na [TALK.cz](https://talk.cz).

Jelikož existuje nepřeberné množství podobných doplňků, co jen berou data z webu a servírují videa do Kodi, rozhodl jsem se taky takový zkusit napsat.

Ani pro Kodi ani v Pythonu jsem nikdy nic nepsal, ale s Claudem byla za jedno odpoledne hotová kostra funkčního doplňku a za týden po odpolednách řekl bych slušně fungující doplněk.

## Přihlášení

Bohužel, [TALK.cz](https://talk.cz) používá na přihlašovací stránce reCaptchu přes kterou se mi zatím nepodařilo projít. (A kdo ví, jestli podaří.)

V nastavení je tak záložní varianta se zkopírováním session cookie, což je trochu nepohodlné, protože ta cookie má platnost 1 měsíc, takže se to bude muset pravidelně opakovat.

### Jak na to

- Přihlašte se normálně v prohlížeči na TALK.cz.
- Přejděte do Nástrojů pro vývojáře stiskem F12.
- Najděte hodnotu cookie PHPSESSID a zadejte ji do doplňku<br>![screenshot-4](resources/screenshot-4.png "screenshot-4")
- Otestujte funkčnost tlačítkem **Test přihlášení**

## Co funguje

* **Funkce**
    * Přihlášení přes PHPSESSID (cookie vykopírované z prohlížeče)
    * Kešování popisů epizod a datumů - menší zátěž pro server Talku, značné zrychlení doplňku
    * Skok na čas, kdy skončila YouTube část videa (Tak trochu. Jen spustí video od času nastaveného v nastavení - průměrná délka YouTube části je cca 22 minut)
    * Živé streamy - aktuálně přes otevření doplňku YouTube

* **Menu**
    * **Hledání**
    * **Poslední videa** - Vlastně stránka "Všechna videa".
    * **Populární videa**
    * **Nejlepší videa** - 16 nejlepších videí. Tahle kategorie ani není na webu 😀.
    * **Pokračovat v přehrávání** - Neaktualizuje se při sledování přes Kodi 😌. (Zatím? 🤔)
    * **Tvůrci** - V podmenu jsou všechny aktuální pořady od STANDASHOW po DESIGN TALK.
    * **Archiv** - V podmenu jsou seznamy videí (IRL, HODNOCENÍ HOSTŮ, VOLBY, ...) a archivované pořady (JARDA VS. NAOMI 🪦).

## Co nefunguje

* **Funkce**
    * Přihlášení přes talktv.cz jméno a heslo.
    * Přihlášení přes Patreon.
