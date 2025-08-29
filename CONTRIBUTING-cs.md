# Pokyny pro přispívání

Přispívání do tohoto projektu by mělo být co nejjednodušší a nejtransparentnější, ať už jde o:

- Hlášení chyby
- Diskuzi o současném stavu kódu
- Odesílání oprav
- Navrhování nových funkcí

## Github se používá pro vše

Github se používá k hostování kódu, sledování problémů a požadavků na funkce a také k přijímání pull requestů.

Pull requesty jsou nejlepším způsobem, jak navrhnout změny v kódové bázi.

1. Forkněte repozitář a vytvořte svou větev z `master`.
2. Pokud jste něco změnili, aktualizujte dokumentaci.
3. Ujistěte se, že váš kód prochází lintováním (pomocí black).
4. Otestujte svůj příspěvek.
5. Vytvořte pull request!

## Všechny vaše příspěvky budou pod licencí MIT Software License

Stručně řečeno, když odešlete změny kódu, vaše příspěvky se považují za podléhající stejné [MIT License](http://choosealicense.com/licenses/mit/), která pokrývá projekt. Neváhejte kontaktovat správce, pokud vás to znepokojuje.

## Hlašte chyby pomocí Github [issues](../../issues)

GitHub issues se používají ke sledování veřejných chyb.
Nahlaste chybu [otevřením nového issue](../../issues/new/choose); je to tak jednoduché!

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

Tato vlastní komponenta je založena na osvědčených postupech popsaných zde [integration_blueprint template](https://github.com/custom-components/integration_blueprint).

Dodává se s vývojovým prostředím v kontejneru, které lze snadno spustit,
pokud používáte Visual Studio Code. S tímto kontejnerem budete mít samostatnou
instanci Home Assistant běžící a již nakonfigurovanou s přiloženým
souborem [`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml).

## Licence

Přispíváním souhlasíte s tím, že vaše příspěvky budou licencovány pod licencí MIT.
