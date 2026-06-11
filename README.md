# Monitor terminów ZnanyLekarz

Sprawdza (co ~3 minuty) najbliższy wolny termin u **Martyny
Sacharewicz (fizjoterapeuta, Białystok)** i wysyła powiadomienie push na telefon, gdy
pojawi się termin **wcześniejszy** niż dotychczas znany. Działa w chmurze
(GitHub Actions) — Twój komputer może być wyłączony. Całość jest darmowa.

## Jak to działa

1. GitHub Actions uruchamia zadanie co 5 minut (częściej harmonogram GitHuba
   nie pozwala), a każde zadanie sprawdza stronę co ~3 minuty —
   efektywnie wychodzi sprawdzenie co ~2,5–3 minuty.
2. Skrypt pobiera stronę lekarza i wyciąga z niej pole `earliestBookableDate`
   (najwcześniejszy rezerwowalny termin, osobno dla każdej usługi — brany jest
   najwcześniejszy ze wszystkich).
3. Porównuje go z ostatnio zapisanym stanem (`state.json`, commitowany do repo).
4. Jeśli nowy termin jest wcześniejszy — wysyła push przez [ntfy.sh](https://ntfy.sh)
   z najwyższym priorytetem. Kliknięcie powiadomienia otwiera stronę rezerwacji.

## Konfiguracja krok po kroku (~10 minut)

### 1. Telefon — aplikacja ntfy

1. Zainstaluj aplikację **ntfy** (Google Play / App Store).
2. W aplikacji: **+ / Subscribe to topic** i wpisz **losową, trudną do
   odgadnięcia nazwę**, np. `terminy-fizjo-x7k2p9q4`.
   ⚠️ Nazwa tematu działa jak hasło — każdy, kto ją zna, może czytać i wysyłać
   powiadomienia. Nie używaj oczywistych nazw.
3. Zezwól aplikacji na powiadomienia (i wyłącz dla niej oszczędzanie baterii,
   żeby push przychodził natychmiast).

### 2. GitHub — repozytorium

1. Załóż darmowe konto na [github.com](https://github.com) (jeśli nie masz).
2. Utwórz **nowe publiczne repozytorium** (np. `termin-monitor`).
   - Repo musi być **publiczne**, bo wtedy GitHub Actions jest darmowe bez
     limitu minut. W repo prywatnym darmowy limit (2000 min/mies.) starcza
     tylko na sprawdzanie co ~30 minut.
   - W repo nie ma żadnych prywatnych danych — nazwa tematu ntfy trzymana
     jest w sekrecie, nie w kodzie.
3. Wgraj do repozytorium **zawartość tego folderu** (struktura musi być
   w korzeniu repo):
   - `check_termin.py`
   - `.github/workflows/check.yml`
   - `README.md`

   Najprościej: na stronie repo **Add file → Upload files** i przeciągnij
   pliki. Folder `.github/workflows/` możesz utworzyć przez
   **Add file → Create new file**, wpisując jako nazwę
   `.github/workflows/check.yml` i wklejając treść.

### 3. GitHub — sekret z nazwą tematu

1. W repo: **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: `NTFY_TOPIC`, Secret: nazwa Twojego tematu (np. `terminy-fizjo-x7k2p9q4`).

### 4. Pierwsze uruchomienie (test)

1. Zakładka **Actions** → workflow **"Sprawdzaj terminy ZnanyLekarz"** →
   **Run workflow**.
2. Po ~30 sekundach na telefon powinno przyjść powiadomienie
   _"Monitoring terminow uruchomiony"_ z aktualnym najbliższym terminem.
3. Od tej pory workflow działa sam co ~5 minut.

## Ważne uwagi

- **Punktualność:** GitHub nie gwarantuje dokładnego "co 5 minut" — w godzinach
  szczytu odstęp bywa 5–15 minut. W praktyce wystarcza; terminy u lekarza nie
  znikają w sekundę po pojawieniu się (a jeśli potrzeba szybciej — patrz Plan B).
- **Auto-wyłączenie:** GitHub wyłącza harmonogram po 60 dniach braku aktywności
  w repo. Dostaniesz wtedy e-mail — wystarczy kliknąć "Enable workflow".
- **Ostrzeżenie o awarii:** jeśli przez ~godzinę nie uda się pobrać strony
  (np. ZnanyLekarz zacznie blokować serwery GitHuba), dostaniesz push
  z ostrzeżeniem. Wtedy patrz Plan B.
- **Regulamin:** automatyczne odpytywanie serwisu formalnie narusza regulamin
  ZnanyLekarz. Skala jest śladowa (288 pobrań strony dziennie, mniej niż
  generuje jeden użytkownik klikający po kalendarzu), ale rób to świadomie
  i na własną odpowiedzialność. Warto równolegle włączyć **wbudowane
  powiadomienie** ZnanyLekarz: na stronie wizyty przycisk
  _"Potrzebuję wcześniejszego terminu wizyty"_ (powiadomienie e-mail).
- **Koniec monitoringu:** po umówieniu wizyty wyłącz workflow
  (Actions → workflow → "…" → Disable workflow) albo usuń repo.

## Zmiana lekarza / dostosowanie

- **Inny lekarz:** w `.github/workflows/check.yml` dodaj w sekcji `env`
  zmienną `DOCTOR_URL` z adresem profilu, np.:

  ```yaml
        env:
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
          DOCTOR_URL: "https://www.znanylekarz.pl/inny-lekarz/specjalizacja/miasto"
  ```

- **Inny odstęp:** zmień `cron: "*/5 * * * *"` (np. `*/10` = co 10 minut).

## Plan B (gdyby GitHub był blokowany przez ZnanyLekarz)

Skrypt jest uniwersalny — potrzebuje tylko Pythona 3 i internetu. Można go
uruchamiać co 5 minut na:

- **Raspberry Pi / starym laptopie w domu** (cron / Harmonogram zadań Windows) —
  domowe IP, praktycznie zero ryzyka blokady,
- **tanim VPS** (~15–25 zł/mies.),
- **Cloudflare Workers** (wymaga przepisania na JavaScript).

Gdyby przyszło ostrzeżenie o awarii — wróć do tej rozmowy w Claude Code,
pomoże przenieść monitoring.
