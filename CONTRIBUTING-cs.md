# Pokyny pro přispívání

Přispívání do tohoto projektu by mělo být co nejjednodušší a nejtransparentnější, ať už jde o:

- Hlášení chyby
- Diskuzi o současném stavu kódu
- Odesílání oprav
- Navrhování nových funkcí

## GitHub se používá pro vše

GitHub se používá k hostování kódu, sledování problémů a požadavků na funkce i přijímání pull requestů.

Pull requesty (PR) jsou skvělým způsobem, jak navrhovat změny v kódové bázi. Tým Versatile Thermostat za dobu existence projektu přijal mnoho PR a tyto příspěvky významně přispěly k jeho úspěchu. Celé komunitě jsme za její příspěvky velmi vděční.

## Jak probíhá kontrola PR

S rozšířením nástrojů umělé inteligence dnes dokáže připravit PR téměř každý. Některé jsou kvalitní a jsou začleněny, jiné přijmout nelze.

Počet PR výrazně vzrostl. Jejich kontrola probíhá převážně ručně a zaměřuje se zejména na dvě věci:

- kvalitu navrženého řešení;
- jeho soulad s budoucím směřováním a vizí Versatile Thermostatu.

PR řešící velmi specifickou potřebu — například odlišné chování zařízení nebo individuální způsob používání integrace — nemusí být možné přijmout. Zejména pokud zvyšuje složitost a představuje riziko pro ostatní uživatele, je třeba její přínos posoudit s ohledem na tyto důsledky.

Již není možné podrobně kontrolovat každou příchozí PR. Musíme je proto třídit a upřednostňovat ty, které přinášejí skutečnou hodnotu produktu nebo komunitě.

Od roku 2025 existuje mechanismus, který umožňuje komukoli vyvíjet rozšíření bez změny integrace Versatile Thermostat a bez rizika pro ostatní uživatele: pluginy. Jsou založeny na modulu [`vtherm_api`](https://github.com/jmcollin78/vtherm_api).

Než navrhnete PR, zvažte prosím, zda by váš požadavek nemohl řešit plugin, který si nainstalují pouze příslušní uživatelé.

Pokud si nejste jisti, zda je změna vhodná nebo zda by mohla být přijata, obraťte se na správce ještě před zahájením vývoje. Navrhovaný přístup tak bude možné včas prodiskutovat.

Odmítnutí PR může být nepříjemné, není však osobní: cílem rozhodnutí je chránit integraci a zkušenost všech uživatelů. Děkujeme za pochopení.

## Navrhování změn

1. Forkněte repozitář a vytvořte svou větev z `master`.
2. Pokud jste něco změnili, aktualizujte dokumentaci.
3. Zajistěte formátování kódu pomocí Black.
4. Otestujte svůj příspěvek.
5. Odešlete svou PR.

## Všechny vaše příspěvky budou pod licencí MIT Software License

Stručně řečeno, když odešlete změny kódu, vaše příspěvky se považují za podléhající stejné [MIT License](http://choosealicense.com/licenses/mit/), která pokrývá projekt. Neváhejte kontaktovat správce, pokud vás to znepokojuje.

## Hlašte chyby pomocí [issues](../../issues) na GitHubu

GitHub issues se používají ke sledování veřejných chyb.
Nahlaste chybu [otevřením nového issue](../../issues/new/choose).

## Pište zprávy o chybách s detaily, pozadím a ukázkovým kódem

**Skvělé hlášení chyb** obvykle mají:

- Rychlé shrnutí a/nebo pozadí
- Kroky k reprodukci
  - Buďte konkrétní!
  - Pokud můžete, uveďte ukázkový kód.
- Co jste očekávali, že se stane
- Co se skutečně stalo
- Poznámky (případně včetně toho, proč si myslíte, že by se to mohlo dít, nebo věci, které jste zkusili a nefungovaly)

Lidé *milují* důkladné zprávy o chybách. To není žert.

## Používejte konzistentní styl kódování

Používejte [black](https://github.com/ambv/black) k zajištění toho, že kód dodržuje styl.

## Otestujte úpravy svého kódu

Tato vlastní komponenta vychází z osvědčených postupů popsaných v [šabloně integrace](https://github.com/custom-components/integration_blueprint).

Dodává se s vývojovým prostředím v kontejneru, které lze snadno spustit,
pokud používáte Visual Studio Code. Tento kontejner spustí samostatnou instanci
Home Assistantu, která je již nakonfigurována pomocí přiloženého souboru
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml).

## Licence

Přispíváním souhlasíte s tím, že vaše příspěvky budou licencovány pod licencí MIT.
