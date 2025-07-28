# Jak nainstalovat Versatile Thermostat?

## Instalace přes HACS (Doporučeno)

1. Nainstalujte [HACS](https://hacs.xyz/). Tímto způsobem budete automaticky dostávat aktualizace.
2. Integrace Versatile Thermostat je nyní dostupná přímo z rozhraní HACS (záložka Integrations).
3. Vyhledejte a nainstalujte "Versatile Thermostat" v HACS a klikněte na "Install".
4. Restartujte Home Assistant.
5. Poté můžete přidat integraci Versatile Thermostat na stránce Nastavení / Integrace. Přidejte tolik termostatů, kolik potřebujete (obvykle jeden na radiátor nebo skupinu radiátorů, které je třeba ovládat, nebo na čerpadlo v případě centralizovaného topného systému).

## Ruční instalace

1. Pomocí nástroje dle vašeho výběru otevřete adresář konfigurace Home Assistant (kde najdete `configuration.yaml`).
2. Pokud nemáte adresář `custom_components`, musíte ho vytvořit.
3. Uvnitř adresáře `custom_components` vytvořte novou složku nazvanou `versatile_thermostat`.
4. Stáhněte _všechny_ soubory z adresáře `custom_components/versatile_thermostat/` (složka) v tomto repositáři.
5. Umístěte stažené soubory do nové složky, kterou jste vytvořili.
6. Restartujte Home Assistant.
7. Nakonfigurujte novou integraci Versatile Thermostat.
