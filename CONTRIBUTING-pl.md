# Zasady współpracy

Twój wkład w ten projekt powinien być jak najprostszy i najbardziej przejrzysty, niezależnie od tego, czy chodzi o:

- Zgłoszenie błędu
- Omówienie aktualnego stanu kodu
- Przesłanie poprawki
- Proponowanie nowych funkcji

## Github służy do wszystkiego

**Github** służy do hostowania kodu, śledzenia problemów i próśb o funkcje, a także do akceptowania _*pull requestów*_.

_*Pull requesty*_ to najlepszy sposób na proponowanie zmian w bazie kodu.

1. Wykonaj _*fork*_ repozytorium i utwórz gałąź `master`,
2. Jeśli coś zmieniłeś, koniecznie zaktualizuj dokumentację w jasny i spójny sposób, stosując _*najlepsze praktyki kodowania*_,
3. Upewnij się, że Twój kod jest _*lintowany*_ (używając czarnego koloru),
4. Przetestuj swoje zmiany,
5. Zgłoś _*pull request*_!


## Wszelkie Twoje zgłoszenia będą podlegać licencji MIT Software License.

Krótko mówiąc, gdy przesyłasz zmiany w kodzie, uznaje się, że Twoje zgłoszenia podlegają tej samej [licencji MIT](http://choosealicense.com/licenses/mit/), która obejmuje projekt. W razie wątpliwości skontaktuj się z deweloperami kodu.

## Zgłaszaj błędy za pomocą [problemów](../../issues) w GitHubie

Zgłoszenia w GitHubie służą do śledzenia publicznych błędów.
Zgłoś błąd, [otwierając nowe zgłoszenie](../../issues/new/choose). To takie proste..

## Twórz zgłoszenia błędów ze szczegółami, opisem kontekstu i przykładowym kodem.

**Dobre zgłoszenia błędów** zazwyczaj zawierają:

- Krótkie podsumowanie i/lub kontekst błędu
- Kroki do odtworzenia błędu
- Bądź konkretny!
- Podaj przykładowy kod, jeśli to możliwe.
- Czego się spodziewałeś
- Co się faktycznie dzieje
- Notatki (ewentualnie z wyjaśnieniem, dlaczego tak się dzieje lub co próbowałeś, ale nie zadziałało)

Ludzie *uwielbiają* dokładne raporty o błędach!

## Używaj spójnego stylu kodowania

Użyj [black](https://github.com/ambv/black), aby upewnić się, że kod jest zgodny ze stylem.

## Przetestuj swoją modyfikację kodu

Ten niestandardowy komponent jest oparty na najlepszych praktykach, opisanych w [szablonie _*blueprint*_ integracji](https://github.com/custom-components/integration_blueprint).

Dostarczany jest ze środowiskiem programistycznym w kontenerze, łatwym do uruchomienia, jeśli używasz _*Visual Studio Code*_. Dzięki temu kontenerowi będziesz mieć autonomiczną instancję _*Home Assistant*_ działającą i skonfigurowaną za pomocą dołączonego pliku [`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml)
.

## Licencja

Uczstnicząc w tym projekcie, wyrażasz zgodę na licencjonowanie swoich materiałów na podstawie licencji **MIT**.
