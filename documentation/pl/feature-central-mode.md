# Centralne sterowanie

- [Centralne sterowanie](#centralized-control)
  - [Konfiguracja centralnego sterowania](#configuration-of-centralized-control)
  - [Zastosowanie](#usage)

Funkcja ta pozwala sterować wszystkimi termostatami _VTherm_ z jednego punktu kontrolnego. Typowym przypadkiem użycia jest sytuacja, gdy wyjeżdżasz na dłuższy czas i chcesz ustawić wszystkie termostaty w tryb ochrony przed mrozem, a po powrocie przywrócić je do stanu początkowego.

Centralne sterowanie odbywa się z poziomu specjalnego termostatu _VTherm_ o nazwie 'Konfiguracja główna'. Zobacz [tutaj](creation.md#centralized-configuration), aby uzyskać więcej informacji.

## Konfiguracja centralnego sterowania

Jeśli skonfigurowałeś centralną konfigurację, pojawi się nowa encja o nazwie `select.central_mode`, która pozwala sterować wszystkimi termostatami _VTherm_ za pomocą jednej akcji.

![central_mode](images/central-mode.png)

Ta encja pojawia się jako lista wyboru zawierająca następujące opcje:
1. `Auto`: „normalny” tryb, w którym każdy termostat _VTherm_ działa autonomicznie,
2. `Zatrzymany`: wszystkie termostaty _VTherm_ są wyłączone (`hvac_off`),
3. `Tylko grzanie`: wszystkie termostaty _VTherm_ są ustawione w tryb grzania, jeśli jest obsługiwany, w przeciwnym razie są wyłączone,
4. `Tylko chłodzenie`: wszystkie termostaty _VTherm_ są ustawione w tryb chłodzenia, jeśli jest obsługiwany, w przeciwnym razie są wyłączone,
5. `Ochrona przeciw zamarzaniu`: wszystkie termostaty _VTherm_ są ustawione w tryb ochrony przed mrozem, jeśli jest obsługiwany, w przeciwnym razie są wyłączone.

## Zastosowanie

Aby termostat _VTherm_ mógł być sterowany centralnie, jego atrybut konfiguracyjny o nazwie `use_central_mode` musi mieć wartość `true`. Ten atrybut jest dostępny na stronie konfiguracji 'Atrybuty główne'.

![central_mode](images/use-central-mode.png)

Oznacza to, że możesz sterować wszystkimi termostatami _VTherm_ (tymi wyraźnie wskazanymi) za pomocą jednego elementu sterowania.
