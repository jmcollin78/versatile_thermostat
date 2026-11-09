# Zasady współpracy

Twój wkład w ten projekt powinien być jak najprostszy i najbardziej przejrzysty, niezależnie od tego, czy chodzi o:

- Zgłoszenie błędu
- Omówienie aktualnego stanu kodu
- Przesłanie poprawki
- Proponowanie nowych funkcji

## GitHub służy do wszystkiego

**GitHub** służy do hostowania kodu, śledzenia problemów i próśb o nowe funkcje, a także do przyjmowania _*pull requestów*_ (PR).

_*Pull requesty*_ to świetny sposób na proponowanie zmian w bazie kodu. W swojej historii zespół Versatile Thermostat zaakceptował wiele PR, a te wkłady w znacznym stopniu przyczyniły się do sukcesu projektu. Jesteśmy bardzo wdzięczni całej społeczności za jej zaangażowanie.

## Jak są przeglądane PR

Wraz z rozwojem narzędzi sztucznej inteligencji niemal każdy może dziś przygotować PR. Niektóre są wysokiej jakości i zostają włączone do projektu, innych nie można zaakceptować.

Liczba PR znacznie wzrosła. Ich przegląd odbywa się głównie ręcznie i obejmuje przede wszystkim dwa aspekty:

- jakość proponowanego rozwiązania;
- jego zgodność z przyszłym kierunkiem rozwoju i wizją Versatile Thermostat.

PR dotyczący bardzo specyficznej potrzeby — na przykład nietypowego zachowania urządzenia lub indywidualnego sposobu korzystania z integracji — nie zawsze może zostać zaakceptowany. Zwłaszcza jeśli zwiększa złożoność i stwarza ryzyko dla pozostałych użytkowników, jego korzyści należy rozważyć w świetle tych konsekwencji.

Nie jesteśmy już w stanie szczegółowo analizować każdej nadchodzącej PR. Musimy więc dokonywać selekcji i priorytetowo traktować te, które wnoszą rzeczywistą wartość dla produktu lub społeczności.

Od 2025 roku istnieje mechanizm pozwalający każdemu tworzyć rozszerzenia bez modyfikowania integracji Versatile Thermostat i bez narażania innych użytkowników: pluginy. Są oparte na module [`vtherm_api`](https://github.com/jmcollin78/vtherm_api).

Przed zgłoszeniem PR zastanów się, czy Twoja potrzeba nie mogłaby zostać zrealizowana jako plugin instalowany wyłącznie przez zainteresowanych użytkowników.

Jeśli nie masz pewności, czy zmiana jest odpowiednia lub czy może zostać zaakceptowana, skontaktuj się z maintainerem przed rozpoczęciem prac. Dzięki temu proponowane podejście będzie można omówić z wyprzedzeniem.

Odrzucenie PR może być przykre, ale nie jest niczym osobistym: decyzja ma na celu ochronę integracji i komfortu wszystkich użytkowników. Dziękujemy za zrozumienie.

## Proponowanie zmian

1. Wykonaj _*fork*_ repozytorium i utwórz gałąź na podstawie `master`.
2. Jeśli coś zmienisz, zaktualizuj dokumentację.
3. Upewnij się, że kod jest sformatowany za pomocą Black.
4. Przetestuj swoje zmiany.
5. Zgłoś swoją PR.


## Wszelkie Twoje zgłoszenia będą podlegać licencji MIT Software License.

Krótko mówiąc, gdy przesyłasz zmiany w kodzie, uznaje się, że Twoje zgłoszenia podlegają tej samej [licencji MIT](http://choosealicense.com/licenses/mit/), która obejmuje projekt. W razie wątpliwości skontaktuj się z deweloperami kodu.

## Zgłaszaj błędy za pomocą [zgłoszeń](../../issues) w GitHubie

Zgłoszenia w GitHubie służą do śledzenia publicznych błędów.
Zgłoś błąd, [otwierając nowe zgłoszenie](../../issues/new/choose).

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

Ten niestandardowy komponent jest zgodny z najlepszymi praktykami opisanymi w [szablonie integracji](https://github.com/custom-components/integration_blueprint).

Dostarczany jest ze środowiskiem programistycznym w kontenerze, łatwym do uruchomienia,
jeśli używasz _*Visual Studio Code*_. Kontener uruchamia samodzielną instancję
_*Home Assistant*_, już skonfigurowaną za pomocą dołączonego pliku
[`.devcontainer/configuration.yaml`](./.devcontainer/configuration.yaml).

## Licencja

Uczstnicząc w tym projekcie, wyrażasz zgodę na licencjonowanie swoich materiałów na podstawie licencji **MIT**.
