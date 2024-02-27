import pandas as pd


def main():
    df = pd.read_csv('history_flats.csv')
    df['Время'] = pd.Timestamp.stdf['Время']
    print(df.head(9).to_string())
    print("...")
    print("Save? Y/N ", end='')
    choose = input()
    if choose.lower() == "y":
        df.to_csv('history_flats.csv', index=False)
        print("Saved")


if __name__ == "__main__":
    main()
