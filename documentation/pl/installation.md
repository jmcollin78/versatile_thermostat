# Jak zainstalować Versatile Thermostat?

## Instalacja z HACS (rekomendowana)

1. Zainstaluj [HACS](https://hacs.xyz/). W ten sposób będziesz otrzymywać informacje o dostępnych aktualizacjach integracji.
2. Integracja `Versatile Thermostat` jest dostępna bezpośrednio z okna interfejsu HACS (zakładka `Integracje`).
3. Znajdź "Versatile Thermostat" w HACS i kliknij "Pobierz".
4. Ponownie uruchom Home Assistant.

## Instalacja manualna

1. Korzystając z wybranego narzędzia, otwórz folder konfiguracji Home Assistant (tam znajdziesz plik `configuration.yaml`).
2. Jeśli nie masz folderu `custom_components`, utworz go.
3. Wewnątrz folderu `custom_components` utwórz nowy folder o nazwie `versatile_thermostat`.
4. Pobierz _wszystkie_ pliki z katalogu `custom_components/versatile_thermostat/` z tego repozytorium.
5. Umieść pobrane pliki w nowo utworzonym folderze.
6. Ponownie uruchom Home Assistant.
<h1></h1>
<b>Teraz możesz dodać pobraną właśnie integrację na stronie <i>Ustawienia -> Urządzenia oraz Usługi</i>. </b> Dodaj tyle termostatów, ile potrzebujesz (zwykle jeden termostat na każdy grzejnik lub grupę grzejników, albo jeden termostat na cały centralny system ogrzewania).
