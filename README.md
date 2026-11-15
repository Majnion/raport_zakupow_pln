# Raport zakupów w PLN

Program w Pythonie, który wczytuje zamówienia zakupowe z pliku CSV (kwoty w różnych walutach), przelicza je na złote według aktualnych kursów NBP i tworzy zestawienie kosztów per dostawca. Powstał jako ćwiczenie łączące obsługę błędów, API, SQL i pandas w jednym programie.

## Jak działa

1. Wczytuje `zakupy.csv` i pomija wiersze, w których kwota nie jest liczbą albo nie jest dodatnia (z komunikatem, który wiersz i dlaczego).
2. Dla każdej waluty z pliku pobiera **raz** ostatni średni kurs z tabeli A API NBP. Gdy kursu nie da się pobrać (brak internetu, nieistniejąca waluta), wiersze w tej walucie są pomijane.
3. Przelicza każdą kwotę na PLN (kwota × kurs, zaokrąglone do 2 miejsc).
4. Zapisuje zamówienia do bazy SQLite `zakupy.db`. Ponowne uruchomienie nie duplikuje danych (`INSERT OR REPLACE` po numerze zamówienia).
5. Zapytaniem SQL z `GROUP BY` liczy dla każdego dostawcy liczbę zamówień i sumę w PLN, posortowane malejąco.
6. Zapisuje zestawienie do `raport_zakupy.csv` (do otwarcia w polskim Excelu) i `raport_zakupy.json`.
7. W konsoli wypisuje, ile wierszy wczytano i pominięto, oraz dostawcę z największą sumą.

## Wymagania

- Python 3.12 lub nowszy (testowane na 3.14)
- Biblioteki: `requests`, `pandas`

```
pip install requests pandas
```

## Uruchomienie

```
python main.py
```

Wymagane jest połączenie z internetem (kursy NBP).

## Plik wejściowy

`zakupy.csv`: separator `;`, kodowanie UTF-8, kolumny `nr`, `dostawca`, `waluta`, `kwota`. Przykład (zawiera celowo błędne wiersze, żeby pokazać obsługę błędów):

```
nr;dostawca;waluta;kwota
ZK-1;Metalex;EUR;1200.50
ZK-4;Plastik;USD;brak
ZK-5;Gumex;XXX;300
ZK-6;Gumex;EUR;0
```

## Wynik

- `zakupy.db`: baza SQLite z tabelą `zakupy` (`nr`, `dostawca`, `waluta`, `kwota`, `kurs`, `kwota_pln`)
- `raport_zakupy.csv`: kolumny `dostawca`, `zamowienia`, `suma_pln`; separator `;`, przecinek dziesiętny, kodowanie UTF-8 z BOM (poprawne otwarcie w Excelu)
- `raport_zakupy.json`: to samo zestawienie jako lista obiektów
- Przykładowe wyjście w konsoli dla pliku wejściowego z repozytorium:

```
Wiersz 4 pominięty: kwota="brak" nie jest liczbą
Wiersz 6 pominięty: kwota nie jest dodatnia
Nie udało się pobrać kursu: XXX
Wiersz 5 pominięty: brak kursu dla XXX
Wczytano: 4, pominięto: 3
Plastik
```

Pliki wynikowe są wpisane do `.gitignore`, więc nie ma ich w repozytorium. Powstają po uruchomieniu programu.

## Znane ograniczenia

- Rekord z pliku zakupy.csv nadpisuje rekord o tym samym unikalnym id