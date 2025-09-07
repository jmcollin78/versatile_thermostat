# Rychlý start

Tato stránka popisuje kroky k rychlému nastavení základního, ale funkčního _VTherm_. Je strukturována podle typu vybavení.

- [Rychlý start](#rychlý-start)
  - [Nodon SIN-4-FP-21 nebo podobný (pilotní drát)](#nodon-sin-4-fp-21-nebo-podobný-pilotní-drát)
  - [Heatzy, eCosy nebo podobný (`climate` entita)](#heatzy-ecosy-nebo-podobný-climate-entita)
  - [Jednoduchý spínač jako Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...](#jednoduchý-spínač-jako-aqara-t1-nous-b2z-sonoff-zbmini-sonoff-pow-)
  - [Sonoff TRVZB nebo podobný (TRV s ovládáním ventilu)](#sonoff-trvzb-nebo-podobný-trv-s-ovládáním-ventilu)
  - [Reverzibilní tepelná čerpadla, klimatizace nebo zařízení ovládaná prostřednictvím `climate` entity](#reverzibilní-tepelná-čerpadla-klimatizace-nebo-zařízení-ovládaná-prostřednictvím-climate-entity)
- [Další kroky](#další-kroky)
- [Výzva k přispívání](#výzva-k-přispívání)

## Nodon SIN-4-FP-21 nebo podobný (pilotní drát)

Tento modul umožňuje ovládání radiátoru prostřednictvím pilotního drátu. Objevuje se v _HA_ jako entita `select`, která umožňuje vybrat topný preset k aplikaci.

_VTherm_ bude regulovat teplotu periodickou změnou preset prostřednictvím přizpůsobených příkazů, dokud není dosaženo cílové teploty.

Aby to fungovalo, preset používaný pro ovládání topení musí být vyšší než maximální teplota, kterou budete potřebovat (24°C je dobrá hodnota).

Pro integraci do _VTherm_ musíte:
1. Vytvořit _VTherm_ typu `over_switch`. Viz [vytvoření _VTherm_](creation.md),
2. Přiřadit mu hlavní atributy (název, senzor teploty místnosti a senzor venkovní teploty minimálně). Viz [hlavní atributy](base-attributes.md),
3. Přiřadit jedno nebo více podkladových zařízení k ovládání. Podkladové zařízení zde je entita `select`, která ovládá Nodon. Viz [podkladová zařízení](over-switch.md),
4. Poskytnout vlastní příkazy zapnutí/vypnutí (povinné pro Nodon). Viz [přizpůsobení příkazů](over-switch.md#přizpůsobení-příkazů). Vlastní příkazy následují formát `select_option/option:<preset>` jak je uvedeno v odkazu.

Po dokončení těchto čtyř kroků budete mít plně funkční _VTherm_, který ovládá váš Nodon nebo podobné zařízení.

## Heatzy, eCosy nebo podobný (`climate` entita)

Tento modul umožňuje ovládání radiátoru, který se objevuje v _HA_ jako entita `climate`, umožňující vám vybrat topný preset nebo režim (Heat / Cool / Off).

_VTherm_ bude regulovat teplotu zapínáním/vypínáním zařízení prostřednictvím přizpůsobených příkazů v pravidelných intervalech, dokud není dosaženo cílové teploty.

Pro integraci do _VTherm_ musíte:
1. Vytvořit _VTherm_ typu `over_switch`. Viz [vytvoření _VTherm_](creation.md),
2. Přiřadit mu hlavní atributy (název, senzor teploty místnosti a senzor venkovní teploty minimálně). Viz [hlavní atributy](base-attributes.md),
3. Přiřadit jedno nebo více podkladových zařízení k ovládání. Podkladové zařízení zde je entita `climate`, která ovládá Heatzy nebo eCosy. Viz [podkladová zařízení](over-switch.md),
4. Poskytnout vlastní příkazy zapnutí/vypnutí (povinné). Viz [přizpůsobení příkazů](over-switch.md#přizpůsobení-příkazů). Vlastní příkazy následují formát `set_hvac_mode/hvac_mode:<mode>` nebo `set_preset_mode/preset_mode:<preset>` jak je uvedeno v odkazu.

Po dokončení těchto čtyř kroků budete mít plně funkční _VTherm_, který ovládá váš Heatzy, eCosy nebo podobné zařízení.

## Jednoduchý spínač jako Aqara T1, Nous B2Z, Sonoff ZBMini, Sonoff POW, ...

Tento modul umožňuje ovládání radiátoru prostřednictvím jednoduchého spínače. Objevuje se v _HA_ jako entita `switch`, která přímo zapíná nebo vypína radiátor.

_VTherm_ bude regulovat teplotu periodickým zapínáním a vypínáním `switch`, dokud není dosaženo cílové teploty.

Pro integraci do _VTherm_ musíte:
1. Vytvořit _VTherm_ typu `over_switch`. Viz [vytvoření _VTherm_](creation.md),
2. Přiřadit mu hlavní atributy (název, senzor teploty místnosti a senzor venkovní teploty minimálně). Viz [hlavní atributy](base-attributes.md),
3. Přiřadit jedno nebo více podkladových zařízení k ovládání. Podkladové zařízení zde je entita `switch`, která ovládá spínač. Viz [podkladová zařízení](over-switch.md).

Po dokončení těchto tří kroků budete mít plně funkční _VTherm_, který ovládá váš `switch` nebo podobné zařízení.

## Sonoff TRVZB nebo podobný (TRV s ovládáním ventilu)

Tento typ zařízení _TRV_ ovládá otevření ventilu, který umožňuje více nebo méně horké vody z kotle nebo tepelného čerpadla protékat. Objevuje se v _HA_ jako entita `climate` spolu s entitami `number`, které ovládají ventil. Tyto entity `number` mohou být skryté a v některých případech je třeba je explicitně přidat.

_VTherm_ bude upravovat stupeň otevření ventilu, dokud není dosaženo cílové teploty.

Pro integraci do _VTherm_ musíte:
1. Vytvořit _VTherm_ typu `over_climate`. Viz [vytvoření _VTherm_](creation.md),
2. Přiřadit mu hlavní atributy (název, senzor teploty místnosti a senzor venkovní teploty minimálně). Viz [hlavní atributy](base-attributes.md),
3. Přiřadit jedno nebo více podkladových zařízení k ovládání. Podkladové zařízení zde je entita `climate`, která ovládá TRV. Viz [podkladová zařízení](over-climate.md),
4. Specifikovat typ regulace pouze jako `Přímé ovládání ventilu`. Nechte možnost `Kompenzovat podkladovou teplotu` nezaškrtnutou. Viz [auto-regulace](over-climate.md#auto-regulation),
5. Poskytnout entity `number` pojmenované `opening_degree`, `closing_degree` a `calibration_offset`. Viz [podkladová zařízení](over-switch.md).

Aby to fungovalo, `closing degree` musí být nastaven na maximum (100%). Nepovolujte okamžitě možnost `Sledovat změnu podkladové teploty`, dokud neověříte, že tato základní konfigurace funguje správně.

Po dokončení těchto pěti kroků budete mít plně funkční _VTherm_, který ovládá váš Sonoff TRVZB nebo podobné zařízení.

## Reverzibilní tepelná čerpadla, klimatizace nebo zařízení ovládaná prostřednictvím `climate` entity

Reverzibilní tepelná čerpadla (HP) nebo podobná zařízení jsou reprezentována v _HA_ jako entita `climate`, umožňující vám vybrat topný preset nebo režim (Heat / Cool / Off).

_VTherm_ bude regulovat teplotu ovládáním cílové teploty a režimu zařízení prostřednictvím příkazů zaslaných podkladové entitě `climate`.

Pro integraci do _VTherm_ potřebujete:
1. Vytvořit _VTherm_ typu `over_climate`. Viz [vytvoření _VTherm_](creation.md),
2. Přiřadit mu hlavní atributy (název, senzor teploty místnosti a senzor venkovní teploty minimálně). Viz [hlavní atributy](base-attributes.md),
3. Definovat jedno nebo více podkladových zařízení k ovládání. Podkladová entita zde je entita `climate`, která spravuje tepelné čerpadlo nebo klimatizaci. Viz [podkladová zařízení](over-climate.md),

Po těchto třech krocích budete mít plně funkční _VTherm_ pro ovládání vašeho tepelného čerpadla, klimatizace nebo podobného zařízení.

Pro pokročilejší použití může být nutná samo-regulace v závislosti na tom, jak dobře vaše zařízení funguje. Samo-regulace zahrnuje _VTherm_ mírně upravující cílovou teplotu, aby povzbudil zařízení k většímu nebo menšímu topení/chlazení, dokud není dosaženo požadované cílové teploty. Samo-regulace je podrobně vysvětlena zde: [samo-regulace](self-regulation.md).

# Další kroky

Jakmile je vytvořen, musíte nakonfigurovat preset teploty. Viz [presety](feature-presets.md) pro minimální konfiguraci.
Můžete také (volitelné, ale doporučené) nainstalovat dedikovanou UI kartu pro vaše dashboardy. (Viz [VTHerm UI Card](https://github.com/jmcollin78/versatile-thermostat-ui-card))

Jakmile je toto minimální nastavení funkční—a pouze pokud funguje správně—můžete přidat další funkce, jako je detekce přítomnosti, abyste se vyhnuli topení, když nikdo není přítomen. Přidávejte je jednu po druhé, ověřujte, že _VTherm_ reaguje správně v každém kroku před pokračováním na další.

Můžete pak nastavit centralizované konfigurace pro sdílení nastavení napříč všemi instancemi _VTherm_, povolit centrální režim pro jednotné ovládání všech _VTherm_ ([centralizovaná konfigurace](feature-central-mode.md)), nebo integrovat ovládání centrálního kotle ([centrální kotel](feature-central-boiler.md)). Toto není vyčerpávající seznam—prosím, podívejte se na obsah pro úplný seznam funkcí _VTherm_.

# Výzva k přispívání

Tato stránka je otevřena pro přispívání. Neváhejte navrhnout další vybavení a minimální konfigurační nastavení.
