import csv
import json
import requests
import sqlite3
import pandas as pd

def wczytaj_zakupy(nazwa_pliku):
    zakupy = []

    try:
        with open(nazwa_pliku, "r", encoding="utf-8", newline="") as plik:
            reader_csv = csv.DictReader(plik, delimiter=";")

            for index, row in enumerate(reader_csv, start=1):
                try:
                    row["kwota"] = float(row["kwota"])
                except ValueError:
                    print(f'Wiersz {index} pominięty: kwota="{row["kwota"]}" nie jest liczbą')
                    continue

                if row["kwota"] <= 0:
                    print(f"Wiersz {index} pominięty: kwota nie jest dodatnia")
                    continue

                row["nr_wiersza"] = index
                row["waluta"] = row["waluta"].upper()
                zakupy.append(row)

    except FileNotFoundError:
        return []

    return zakupy


def pobierz_kurs(waluta):
    url = f"https://api.nbp.pl/api/exchangerates/rates/a/{waluta}/last/1/"

    try:
        response = requests.get(url, params={"format": "json"}, timeout=10)
        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException:
        print(f"Nie udało się pobrać kursu: {waluta}")
        return None

    exchange = float(data["rates"][0]["mid"])
    return exchange

def przelicz_na_pln(zakupy):
    waluty = {row["waluta"] for row in zakupy}
    kursy = {waluta: pobierz_kurs(waluta) for waluta in waluty}

    zakupy_oczyszczone = []
    for row in zakupy:
        if kursy[row['waluta']] is None:
            print(f"Wiersz {row['nr_wiersza']} pominięty: brak kursu dla {row['waluta']}")
            continue
        zakupy_oczyszczone.append(row)

    zakupy_policzone = []
    for row in zakupy_oczyszczone:
        row["kurs"] = kursy[row['waluta']]
        row["kwota_pln"] = round(row["kwota"] * row["kurs"], 2)
        zakupy_policzone.append(row)

    return zakupy_policzone


def zapisz_do_bazy(zakupy, nazwa_bazy):
    with sqlite3.connect(nazwa_bazy) as conn:

        cur = conn.cursor()

        cur.execute("""
            create table if not exists zakupy(
                nr TEXT PRIMARY KEY,
                dostawca TEXT,
                waluta TEXT,
                kwota REAL,
                kurs REAL,
                kwota_pln REAL
            )
        """)

        for row in zakupy:
            cur.execute("""
                insert or replace into zakupy (nr, dostawca, waluta, kwota, kurs, kwota_pln)
                values(?, ? ,? ,? , ?, ?)
            """, (row["nr"], row["dostawca"], row["waluta"], row["kwota"], row["kurs"], row["kwota_pln"]))

        cur.execute("""
            select count(*) from zakupy
        """)

        liczba_wierszy = cur.fetchone()[0]
    conn.close()
    return liczba_wierszy

def zestawienie(nazwa_bazy):
    with sqlite3.connect(nazwa_bazy) as conn:

        df = pd.read_sql_query("""
            select dostawca, count(*) as zamowienia, round(sum(kwota_pln),2) as suma_pln from zakupy
            group by dostawca
            order by suma_pln DESC
        """, conn)

    conn.close()
    return df


def zapisz_raport(df, nazwa_csv, nazwa_json):
    df.to_csv(nazwa_csv, index=False, sep=";", encoding="utf-8-sig", decimal=",")

    dane = df.to_dict(orient="records")

    with open(nazwa_json, "w", encoding="utf-8") as plik:
        json.dump(dane, plik, ensure_ascii=False, indent=2)


def policz_wiersze(nazwa_pliku):
    with open(nazwa_pliku, "r", encoding="utf-8", newline="") as plik:
        csv_reader = csv.DictReader(plik, delimiter=";")
        liczba_wczytanych = 0
        for row in csv_reader:
            liczba_wczytanych += 1

    return liczba_wczytanych
    
zakupy = wczytaj_zakupy("zakupy.csv")
zakupy_policzone = przelicz_na_pln(zakupy)
zapisz_do_bazy(zakupy_policzone, "zakupy.db")
df = zestawienie("zakupy.db")
zapisz_raport(df, "raport_zakupy.csv", "raport_zakupy.json")

print(f"Wczytano: {len(zakupy_policzone)}, pominięto: {policz_wiersze("zakupy.csv") - len(zakupy_policzone)}")
max_id = df["suma_pln"].idxmax()
max_dostawca = df.loc[max_id, "dostawca"]
print(max_dostawca)
